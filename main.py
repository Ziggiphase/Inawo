import os
import json
import asyncio
from io import BytesIO
from typing import List
import pandas as pd
import pdfplumber
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from database import get_db, engine
import models
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_vendor 
from pydantic import BaseModel, EmailStr, Field
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

models.Base.metadata.create_all(bind=engine)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- HELPER: VENDOR ALERTS ---
async def notify_vendor(vendor_id: int, message: str, db: Session):
    vendor = db.query(models.Vendor).get(vendor_id)
    if vendor and vendor.telegram_chat_id and bot_application:
        try:
            await bot_application.bot.send_message(chat_id=vendor.telegram_chat_id, text=f"🔔 INAWO ALERT:\n{message}")
        except: pass

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
                        
                        # 1. SETUP SESSION
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session or session.is_ai_paused: return {"status": "skipped"}
                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # 2. HANDLE IMAGES (Receipt Verification)
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            await send_whatsapp_message(sender, "I see your receipt! Verifying payment... 🧐")
                            
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)

                            if "amount" in receipt:
                                amt = float(receipt["amount"])
                                # Find the latest pending order for this customer
                                order = db.query(models.Order).filter(
                                    models.Order.customer_number == sender,
                                    models.Order.status == "pending"
                                ).order_by(models.Order.created_at.desc()).first()

                                if order and abs(order.amount - amt) < 1.0: # Close enough to match
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Payment of ₦{amt} verified! Your order is now being processed.")
                                    await notify_vendor(vendor.id, f"💰 PAID: Order for {sender} verified automatically (₦{amt})", db)
                                else:
                                    await send_whatsapp_message(sender, f"I found a receipt for ₦{amt}, but it doesn't match your pending order. A human will check this shortly.")
                                    await notify_vendor(vendor.id, f"⚠️ PAYMENT MISMATCH: {sender} sent ₦{amt} receipt.", db)
                            return {"status": "success"}

                        # 3. HANDLE TEXT (Order Extraction)
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            # Standard AI Response
                            prompt = f"Concise AI for {vendor.business_name}. {vendor.knowledge_base_text}. Max 2 sentences."
                            result = await inawo_app.ainvoke({"messages": [("system", prompt), ("user", text)]}, {"configurable": {"thread_id": sender}})
                            reply = result["messages"][-1].content
                            await send_whatsapp_message(sender, reply)

                            # Background Order Extraction
                            ext_p = f"Extract order from: '{text}'. Return ONLY JSON: {{\"item\": str, \"total\": float}} or null."
                            ext = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext["messages"][-1].content)
                                if o_data.get("item"):
                                    db.add(models.Order(vendor_id=vendor.id, customer_number=sender, items=o_data['item'], amount=o_data.get('total', 0)))
                                    db.commit()
                                    await notify_vendor(vendor.id, f"📦 NEW ORDER: {o_data['item']} (₦{o_data.get('total', 0)})", db)
                            except: pass

        return {"status": "success"}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}

# ... (Auth, Stats, and Upload routes remain as before) ...
