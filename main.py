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

# --- AI & MESSAGING ---
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

models.Base.metadata.create_all(bind=engine)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class InventoryUpdate(BaseModel):
    items: str

# --- HELPER: VENDOR ALERTS ---
async def notify_vendor(vendor_id: int, message: str, db: Session):
    vendor = db.query(models.Vendor).get(vendor_id)
    if vendor and vendor.telegram_chat_id and bot_application:
        try:
            await bot_application.bot.send_message(chat_id=vendor.telegram_chat_id, text=f"🔔 INAWO ALERT:\n{message}")
        except: pass

# --- NEW: BACKGROUND REMINDER TASK ---
async def start_reminder_loop():
    """Checks for unpaid orders every 2 hours and nudges customers."""
    while True:
        await asyncio.sleep(7200) # Wait 2 hours
        from database import SessionLocal
        db = SessionLocal()
        try:
            # Find pending orders older than 2 hours but younger than 24 hours
            time_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
            unpaid_orders = db.query(models.Order).filter(
                models.Order.status == "pending",
                models.Order.created_at <= time_threshold
            ).all()

            for order in unpaid_orders:
                nudge_msg = f"Hi! Just a friendly reminder about your order for {order.items}. Let us know if you've made payment or need help! 😊"
                await send_whatsapp_message(order.customer_number, nudge_msg)
                print(f"⏰ Sent reminder to {order.customer_number}")
        except Exception as e:
            print(f"Reminder Error: {e}")
        finally:
            db.close()

# --- WHATSAPP WEBHOOK ---
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
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session or session.is_ai_paused: return {"status": "skipped"}
                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # IMAGE HANDLER (Receipts)
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            if "amount" in receipt:
                                amt = float(receipt["amount"])
                                order = db.query(models.Order).filter(models.Order.customer_number == sender, models.Order.status == "pending").order_by(models.Order.created_at.desc()).first()
                                if order and abs(order.amount - amt) < 1.0:
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Payment of ₦{amt} verified! Your order is being processed.")
                                    await notify_vendor(vendor.id, f"💰 PAID: Order from {sender} (₦{amt})", db)
                            return {"status": "success"}

                        # TEXT HANDLER
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender, content=text, role="user"))
                            prompt = f"Concise AI for {vendor.business_name}. {vendor.knowledge_base_text}. STOCK: {vendor.out_of_stock_items}. Max 2 sentences."
                            result = await inawo_app.ainvoke({"messages": [("system", prompt), ("user", text)]}, {"configurable": {"thread_id": sender}})
                            reply = result["messages"][-1].content
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender="AI", content=reply, role="assistant"))
                            db.commit()
                            await send_whatsapp_message(sender, reply)

                            # Extract Order
                            ext_p = f"Extract from: '{text}'. Return ONLY JSON: {{\"item\": str, \"total\": float}} or null."
                            ext = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext["messages"][-1].content)
                                if o_data.get("item"):
                                    db.add(models.Order(vendor_id=vendor.id, customer_number=sender, items=o_data['item'], amount=o_data.get('total', 0)))
                                    db.commit()
                                    await notify_vendor(vendor.id, f"📦 NEW ORDER: {o_data['item']} (₦{o_data.get('total', 0)})", db)
                            except: pass
        return {"status": "success"}
    except Exception as e: return {"status": "error", "detail": str(e)}

# --- DASHBOARD & INVENTORY ---
@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success"}

@app.get("/vendor/stats")
async def get_stats(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    results = db.query(cast(models.Order.created_at, Date).label("day"), func.sum(models.Order.amount).label("total")).filter(models.Order.vendor_id == curr.id).group_by(cast(models.Order.created_at, Date)).all()
    return [{"day": str(r.day), "total": r.total} for r in results]

# --- STARTUP WITH BACKGROUND TASKS ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Inawo API Starting...")
    # 1. Start Reminder Loop
    asyncio.create_task(start_reminder_loop())
    
    # 2. Start Telegram Bot
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
