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
from sqlalchemy import func
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

class VendorSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str

# --- HELPER: VENDOR ALERTS ---
async def notify_vendor(vendor_id: int, message: str, db: Session):
    vendor = db.query(models.Vendor).get(vendor_id)
    if vendor and vendor.telegram_chat_id and bot_application:
        try:
            await bot_application.bot.send_message(chat_id=vendor.telegram_chat_id, text=f"🔔 INAWO ALERT:\n{message}")
        except Exception as e: print(f"Alert error: {e}")

# --- WHATSAPP WEBHOOK ---
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
                        text = msg.get("text", {}).get("body", "")

                        # 1. SESSION & TAKE-OVER CHECK
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session: return {"status": "ignored"}
                        if session.is_ai_paused: return {"status": "human_mode"}

                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # 2. LOG & AI REPLY (Concise)
                        db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender, content=text, role="user"))
                        prompt = f"You are the concise AI for {vendor.business_name}. Context: {vendor.knowledge_base_text}. Out of stock: {vendor.out_of_stock_items}. Max 2 sentences."
                        result = await inawo_app.ainvoke({"messages": [("system", prompt), ("user", text)]}, {"configurable": {"thread_id": sender}})
                        reply = result["messages"][-1].content
                        
                        db.add(models.ChatMessage(vendor_id=vendor.id, sender="AI", content=reply, role="assistant"))
                        db.commit()
                        await send_whatsapp_message(sender, reply)

                        # 3. EXTRACTION (Name, Address, Order)
                        extract_p = f"Extract from: '{text}'. Return ONLY JSON: {{\"item\": str, \"total\": float, \"name\": str, \"address\": str}} or null."
                        ext = await inawo_app.ainvoke([("system", extract_p)])
                        try:
                            ext_data = json.loads(ext["messages"][-1].content)
                            if ext_data.get("name"): session.customer_name = ext_data["name"]
                            if ext_data.get("address"): session.delivery_address = ext_data["address"]
                            if ext_data.get("item"):
                                db.add(models.Order(vendor_id=vendor.id, customer_number=sender, items=ext_data['item'], amount=ext_data.get('total', 0)))
                                await notify_vendor(vendor.id, f"📦 NEW ORDER: {ext_data['item']} from {sender}", db)
                            db.commit()
                        except: pass
        return {"status": "success"}
    except Exception as e: return {"status": "error", "detail": str(e)}

# --- DASHBOARD ROUTES ---
@app.get("/vendor/telegram-link")
async def get_tg_link(curr: models.Vendor = Depends(get_current_vendor)):
    return {"link": f"https://t.me/Inawo_Bot?start=v_{curr.id}"}

@app.post("/vendor/pause-ai")
async def toggle_ai(customer: str, pause: bool, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    s = db.query(models.ChatSession).filter(models.ChatSession.vendor_id == curr.id, models.ChatSession.customer_number == customer).first()
    if s: s.is_ai_paused = pause; db.commit(); return {"status": "success"}
    raise HTTPException(status_code=404)

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).all()

# ... (Auth & Upload routes remain the same as previous main.py) ...
@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    new_v = models.Vendor(email=vendor.email, business_name=vendor.business_name, password_hash=hash_password(vendor.password))
    db.add(new_v); db.commit(); return {"status": "success"}

@app.post("/login")
async def login(vendor: VendorSignup, db: Session = Depends(get_db)):
    v = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if not v or not verify_password(vendor.password, v.password_hash): raise HTTPException(status_code=401)
    return {"access_token": create_access_token(data={"sub": v.email, "id": v.id})}

@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
        except Exception as e: print(f"Bot startup fail: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
