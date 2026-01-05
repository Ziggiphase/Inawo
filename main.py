import os
import json
import asyncio
from typing import List
import pandas as pd
import pdfplumber
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta, timezone

# --- DATABASE & SECURITY ---
from database import get_db, engine
import models
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_vendor 
from pydantic import BaseModel, EmailStr, Field

# --- ROUTER IMPORTS ---
from auth_routes import router as auth_router

# --- AI & MESSAGING ---
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

# Initialize Database Tables
models.Base.metadata.create_all(bind=engine)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS Backend")

# Standard Middleware for Frontend (Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Auth Routes (Login/Signup)
app.include_router(auth_router)

class InventoryUpdate(BaseModel):
    items: str

# --- ROOT ROUTE (Fixes Render 404 & Health Check) ---
@app.get("/")
async def root():
    return {
        "status": "Inawo API Active",
        "engine": "Llama 3.3 70B",
        "time": datetime.now(timezone.utc)
    }

# --- WHATSAPP WEBHOOK ---

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"), 
    token: str = Query(None, alias="hub.verify_token"), 
    challenge: str = Query(None, alias="hub.challenge")
):
    """Verifies the webhook with Meta (Facebook)."""
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Mismatch Error", status_code=403)

@app.post("/webhook")
async def handle_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """The main entry point for all customer WhatsApp messages."""
    data = await request.json()
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    val = change.get("value")
                    if "messages" in val:
                        msg = val["messages"][0]
                        sender = msg["from"]

                        # 1. AUTO-SESSION: Find or Create Customer Session
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session:
                            vendor = db.query(models.Vendor).first() # Default to first vendor for free tier
                            if not vendor: return {"status": "no_vendors_available"}
                            session = models.ChatSession(customer_number=sender, vendor_id=vendor.id)
                            db.add(session); db.commit()

                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # 2. IMAGE HANDLER (Payment Vision)
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            
                            if "amount" in receipt and not receipt.get("error"):
                                # Look for the latest pending order for this number
                                order = db.query(models.Order).filter(
                                    models.Order.customer_number == sender, 
                                    models.Order.status == "pending"
                                ).order_by(models.Order.created_at.desc()).first()
                                
                                if order:
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Receipt for ₦{receipt['amount']} received and verified! Thank you.")
                            return {"status": "success"}

                        # 3. TEXT HANDLER (AI Conversation + Order Extraction)
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            
                            # AI Logic Config
                            config = {
                                "configurable": {
                                    "thread_id": sender,
                                    "business_data": vendor.business_name,
                                    "out_of_stock": vendor.out_of_stock_items or "None"
                                }
                            }
                            
                            # Log user message
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender, content=text, role="user"))
                            db.commit()

                            # Generate AI Reply
                            result = await inawo_app.ainvoke({"messages": [("user", text)]}, config)
                            reply = result["messages"][-1].content
                            
                            # Log and Send Reply
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender="AI", content=reply, role="assistant"))
                            db.commit()
                            await send_whatsapp_message(sender, reply)

                            # BACKGROUND: Extraction (Log potential order in DB)
                            ext_p = f"Extract from: '{text}'. If it's an order, return ONLY JSON: {{\"item\": str, \"total\": float}}. Else return null."
                            ext_res = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext_res["messages"][-1].content)
                                if o_data and o_data.get("item"):
                                    new_order = models.Order(
                                        vendor_id=vendor.id, 
                                        customer_number=sender, 
                                        items=o_data['item'], 
                                        amount=o_data.get('total', 0)
                                    )
                                    db.add(new_order); db.commit()
                            except: pass

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return {"status": "error"}

# --- VENDOR MANAGEMENT ROUTES ---

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Retrieves all orders for the logged-in vendor."""
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).order_by(models.Order.created_at.desc()).all()

@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Updates out-of-stock items for the AI to know."""
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success"}

# --- LIFECYCLE & BACKGROUND TASKS ---

@app.on_event("startup")
async def startup_event():
    """Starts background engines after the API is live."""
    print("🚀 Inawo Engines Starting...")
    
    # 1. Telegram Bot Task
    async def run_bot():
        await asyncio.sleep(10) # Wait for API port to bind
        if bot_application:
            try:
                await bot_application.initialize()
                await bot_application.updater.start_polling(drop_pending_updates=True)
                await bot_application.start()
                print("✅ Telegram Bot Active")
            except Exception as e:
                print(f"❌ Bot Startup Error: {e}")

    asyncio.create_task(run_bot())

if __name__ == "__main__":
    import uvicorn
    # Render uses the PORT env variable
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
