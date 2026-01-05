import os
import json
import asyncio
from typing import List
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta, timezone

# --- INTERNAL IMPORTS ---
from database import get_db, engine
import models
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_vendor 
from pydantic import BaseModel, EmailStr, Field
from auth_routes import router as auth_router
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

# Initialize DB
models.Base.metadata.create_all(bind=engine)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication (Signup/Login)
app.include_router(auth_router)

class InventoryUpdate(BaseModel):
    items: str

# --- 1. HEALTH CHECK ---
@app.get("/")
async def root():
    return {"status": "Inawo API Active", "version": "2.0.0", "time": datetime.now(timezone.utc)}

# --- 2. WHATSAPP WEBHOOK (The Brain) ---

@app.get("/webhook")
async def verify_webhook(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"), challenge: str = Query(None, alias="hub.challenge")):
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Mismatch Error", status_code=403)

@app.post("/webhook")
async def handle_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    val = change.get("value")
                    if "messages" in val:
                        msg = val["messages"][0]
                        sender = msg["from"]

                        # A. Auto-Session Management
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session:
                            vendor = db.query(models.Vendor).first() # Default for Free Version
                            if not vendor: return {"status": "error", "msg": "No vendors found"}
                            session = models.ChatSession(customer_number=sender, vendor_id=vendor.id)
                            db.add(session); db.commit()

                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # B. Image/Receipt Handler
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            
                            if "amount" in receipt and not receipt.get("error"):
                                order = db.query(models.Order).filter(models.Order.customer_number == sender, models.Order.status == "pending").order_by(models.Order.created_at.desc()).first()
                                if order:
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Payment of ₦{receipt['amount']} verified! Processing your order now.")
                            return {"status": "success"}

                        # C. Text/AI Handler
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            
                            # AI Context Configuration
                            config = {
                                "configurable": {
                                    "thread_id": sender,
                                    "business_data": vendor.business_name,
                                    "out_of_stock": vendor.out_of_stock_items or "None"
                                }
                            }
                            
                            # 1. AI Reply
                            result = await inawo_app.ainvoke({"messages": [("user", text)]}, config)
                            reply = result["messages"][-1].content
                            await send_whatsapp_message(sender, reply)

                            # 2. Automated Order Extraction (Silent Background Task)
                            ext_p = f"Analyze: '{text}'. If it is a purchase intent, return JSON: {{\"item\": str, \"total\": float}}. Else return null."
                            ext_res = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext_res["messages"][-1].content)
                                if o_data and o_data.get("item"):
                                    new_order = models.Order(vendor_id=vendor.id, customer_number=sender, items=o_data['item'], amount=o_data.get('total', 0))
                                    db.add(new_order); db.commit()
                            except: pass

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Logic Error: {e}")
        return {"status": "error"}

# --- 3. DASHBOARD & VENDOR TOOLS ---

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).order_by(models.Order.created_at.desc()).all()

@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success"}

@app.get("/vendor/stats")
async def get_stats(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    results = db.query(cast(models.Order.created_at, Date).label("day"), func.sum(models.Order.amount).label("total")).filter(models.Order.vendor_id == curr.id).group_by(cast(models.Order.created_at, Date)).all()
    return [{"day": str(r.day), "total": r.total} for r in results]

@app.get("/vendor/telegram-link")
async def get_tg_link(curr: models.Vendor = Depends(get_current_vendor)):
    return {"link": f"https://t.me/Inawo_Bot?start=v_{curr.id}"}

# --- 4. LIFECYCLE (SAFE STARTUP) ---

@app.on_event("startup")
async def startup_event():
    """Starts the bot in the background only after Render confirms health."""
    async def delayed_start():
        await asyncio.sleep(45) # Increased delay for Render stability
        if bot_application:
            try:
                await bot_application.initialize()
                await bot_application.updater.start_polling(drop_pending_updates=True)
                await bot_application.start()
                print("✅ Telegram Polling Active")
            except Exception as e:
                print(f"❌ Bot Fail: {e}")

    asyncio.create_task(delayed_start())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
