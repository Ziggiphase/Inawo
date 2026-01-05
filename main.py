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
from pydantic import BaseModel
from auth_routes import router as auth_router

# --- AI & MESSAGING SERVICES ---
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

# 1. Initialize Database Tables
models.Base.metadata.create_all(bind=engine)

# 2. Import Bot Application (After models are ready)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS")

# 3. Middleware & Routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

class InventoryUpdate(BaseModel):
    items: str

# --- HEALTH CHECK ---
@app.get("/")
async def root():
    return {"status": "Inawo API Active", "engine": "Llama 3.3 70B", "time": datetime.now(timezone.utc)}

# --- WHATSAPP WEBHOOK (The Brain) ---

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

                        # A. Auto-Session (Free Version Logic)
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session:
                            vendor = db.query(models.Vendor).first() # Auto-assign to first vendor
                            if not vendor: return {"status": "no_vendors"}
                            session = models.ChatSession(customer_number=sender, vendor_id=vendor.id)
                            db.add(session); db.commit()

                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # B. Image/Receipt Processing
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            
                            if "amount" in receipt and not receipt.get("error"):
                                # Mark latest pending order as paid
                                order = db.query(models.Order).filter(
                                    models.Order.customer_number == sender, 
                                    models.Order.status == "pending"
                                ).order_by(models.Order.created_at.desc()).first()
                                
                                if order:
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Receipt for ₦{receipt['amount']} verified! Your order is being processed.")
                            return {"status": "success"}

                        # C. Text/AI Sales Assistant
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            
                            # Config for the LangGraph Brain
                            config = {
                                "configurable": {
                                    "thread_id": sender,
                                    "business_data": vendor.business_name,
                                    "knowledge": vendor.knowledge_base_text,
                                    "out_of_stock": vendor.out_of_stock_items or "None"
                                }
                            }
                            
                            # 1. Generate AI Response
                            result = await inawo_app.ainvoke({"messages": [("user", text)]}, config)
                            reply = result["messages"][-1].content
                            await send_whatsapp_message(sender, reply)

                            # 2. Automated Order Creation (Silent Extraction)
                            ext_p = f"Extract from: '{text}'. If purchase intent, return JSON: {{\"item\": str, \"total\": float}}. Else return null."
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
        print(f"❌ Webhook Logic Error: {e}")
        return {"status": "error"}

# --- VENDOR DASHBOARD ROUTES ---

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Fetch all orders for the logged-in vendor."""
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).order_by(models.Order.created_at.desc()).all()

@app.get("/vendor/stats")
async def get_stats(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Calculate daily sales totals for the dashboard chart."""
    results = db.query(
        cast(models.Order.created_at, Date).label("day"), 
        func.sum(models.Order.amount).label("total")
    ).filter(models.Order.vendor_id == curr.id, models.Order.status == "paid").group_by(cast(models.Order.created_at, Date)).all()
    
    return [{"day": str(r.day), "total": r.total} for r in results]

@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Update out-of-stock list so AI knows not to sell them."""
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success"}

@app.get("/vendor/telegram-link")
async def get_telegram_link(curr: models.Vendor = Depends(get_current_vendor)):
    """Generate the deep-link for the Telegram Bot."""
    return {"link": f"https://t.me/Inawo_Bot?start=v_{curr.id}"}

# --- SAFE STARTUP (Render Support) ---

@app.on_event("startup")
async def startup_event():
    """Starts the Telegram bot in the background after the web server is live."""
    async def delayed_bot_start():
        await asyncio.sleep(45) # Delay to allow Render to pass health checks
        if bot_application:
            try:
                await bot_application.initialize()
                # Ensure no duplicate polling sessions
                try: await bot_application.updater.stop()
                except: pass
                
                await bot_application.updater.start_polling(drop_pending_updates=True)
                await bot_application.start()
                print("✅ Telegram Polling Active")
            except Exception as e:
                print(f"❌ Bot Startup Failure: {e}")

    asyncio.create_task(delayed_bot_start())

if __name__ == "__main__":
    import uvicorn
    # Use environment port for Render/Heroku
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
