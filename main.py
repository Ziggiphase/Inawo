import os
import json
import asyncio
from io import BytesIO
from typing import List

import pandas as pd
import pdfplumber
import docx
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS ---
class VendorSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str
    category: str
    bank_name: str
    account_number: str = Field(..., min_length=10, max_length=10)
    account_name: str

# --- HELPER: VENDOR NOTIFICATIONS ---
async def notify_vendor(vendor_id: int, message: str, db: Session):
    """Sends a Telegram alert to the vendor if they have a chat_id set."""
    vendor = db.query(models.Vendor).get(vendor_id)
    if vendor and vendor.telegram_chat_id:
        try:
            # We use the existing bot instance to send the alert
            await bot_application.bot.send_message(chat_id=vendor.telegram_chat_id, text=f"🔔 INAWO ALERT:\n{message}")
        except Exception as e:
            print(f"⚠️ Failed to notify vendor: {e}")

# --- WHATSAPP WEBHOOK ---

@app.get("/webhook")
@app.get("/webhook/")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if mode == "subscribe" and token == verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Mismatch Error", status_code=403)

@app.post("/webhook")
async def handle_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value")
                    if "messages" in value:
                        message = value["messages"][0]
                        sender_number = message["from"]
                        user_text = message.get("text", {}).get("body", "")

                        # 1. SESSION & HUMAN TAKE-OVER CHECK
                        session_record = db.query(models.ChatSession).filter(
                            models.ChatSession.customer_number == sender_number
                        ).first()
                        
                        if not session_record:
                            return {"status": "ignored", "reason": "no_active_vendor_link"}

                        # If vendor has paused the AI for this customer, we do nothing
                        if session_record.is_ai_paused:
                            print(f"⏸ AI Paused for {sender_number}. Human is in control.")
                            return {"status": "success", "info": "ai_paused"}

                        vendor = db.query(models.Vendor).get(session_record.vendor_id)
                        
                        # 2. LOG CUSTOMER MESSAGE
                        db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender_number, content=user_text, role="user"))

                        # 3. AI GENERATION (SMART, CONCISE, AND PROFILE-AWARE)
                        system_prompt = f"""
                        You are the concise AI Sales Assistant for {vendor.business_name}. 
                        IDENTITY/PRICES: {vendor.knowledge_base_text}
                        OUT OF STOCK: {vendor.out_of_stock_items or 'None'}
                        
                        YOUR GOAL:
                        - Max 2 sentences. Use smart, friendly Nigerian business English.
                        - If the customer provides their name or address, acknowledge it briefly.
                        - If they ask for something OUT OF STOCK, politely suggest an alternative.
                        """
                        
                        inputs = {"messages": [("system", system_prompt), ("user", user_text)]}
                        result = await inawo_app.ainvoke(inputs, {"configurable": {"thread_id": sender_number}})
                        ai_reply = result["messages"][-1].content

                        # 4. LOG AI REPLY & SEND
                        db.add(models.ChatMessage(vendor_id=vendor.id, sender="AI", content=ai_reply, role="assistant"))
                        db.commit()
                        await send_whatsapp_message(sender_number, ai_reply)

                        # 5. DATA EXTRACTION (ADDRESS, NAME, ORDERS)
                        extraction_prompt = f"""
                        Extract data from: '{user_text}'. 
                        Return ONLY JSON: {{"item": str, "total": float, "name": str, "address": str}}
                        If info is missing, use null.
                        """
                        ext_result = await inawo_app.ainvoke([("system", extraction_prompt)])
                        raw_ext = ext_result["messages"][-1].content
                        
                        try:
                            ext_data = json.loads(raw_ext)
                            # Update Profile
                            if ext_data.get("name"): session_record.customer_name = ext_data["name"]
                            if ext_data.get("address"): session_record.delivery_address = ext_data["address"]
                            
                            # Log Order
                            if ext_data.get("item"):
                                new_order = models.Order(
                                    vendor_id=vendor.id,
                                    customer_number=sender_number,
                                    items=ext_data['item'],
                                    amount=ext_data.get('total', 0),
                                    status="pending"
                                )
                                db.add(new_order)
                                await notify_vendor(vendor.id, f"📦 NEW ORDER: {ext_data['item']} from {sender_number}", db)
                            
                            db.commit()
                        except: pass

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return {"status": "error"}

# --- VENDOR MANAGEMENT ROUTES ---

@app.get("/vendor/orders")
async def get_vendor_orders(db: Session = Depends(get_db), current_vendor: models.Vendor = Depends(get_current_vendor)):
    return db.query(models.Order).filter(models.Order.vendor_id == current_vendor.id).order_by(models.Order.created_at.desc()).all()

@app.post("/vendor/pause-ai")
async def toggle_ai(customer_number: str, pause: bool, db: Session = Depends(get_db), current_vendor: models.Vendor = Depends(get_current_vendor)):
    session = db.query(models.ChatSession).filter(models.ChatSession.vendor_id == current_vendor.id, models.ChatSession.customer_number == customer_number).first()
    if session:
        session.is_ai_paused = pause
        db.commit()
        return {"status": "success", "ai_active": not pause}
    raise HTTPException(status_code=404, detail="Session not found")

@app.post("/upload-knowledge")
async def upload_knowledge(file: UploadFile = File(...), db: Session = Depends(get_db), current_vendor: models.Vendor = Depends(get_current_vendor)):
    text_content = ""
    filename = file.filename.lower()
    try:
        if filename.endswith(".pdf"):
            with pdfplumber.open(file.file) as pdf:
                text_content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        elif filename.endswith((".xlsx", ".csv")):
            df = pd.read_excel(file.file) if filename.endswith(".xlsx") else pd.read_csv(file.file)
            text_content = df.to_string()
        
        current_vendor.knowledge_base_text = text_content
        db.commit()
        return {"status": "success", "char_count": len(text_content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendor/chats")
async def get_vendor_chats(db: Session = Depends(get_db), current_vendor: models.Vendor = Depends(get_current_vendor)):
    chats = db.query(models.ChatMessage.sender, func.max(models.ChatMessage.created_at).label("last_msg"))\
             .filter(models.ChatMessage.vendor_id == current_vendor.id)\
             .group_by(models.ChatMessage.sender).all()
    return [{"customer": c.sender, "time": c.last_msg} for c in chats]

# --- LIFECYCLE ---

@app.on_event("startup")
async def startup_event():
    print("🚀 Inawo API stable.")
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
            print("✅ Telegram Bot Active for Notifications")
        except Exception as e: print(f"⚠️ Telegram conflict: {e}")

@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    new_vendor = models.Vendor(email=vendor.email, business_name=vendor.business_name, password_hash=hash_password(vendor.password))
    db.add(new_vendor); db.commit()
    return {"status": "success"}

@app.post("/login")
async def login(vendor: VendorSignup, db: Session = Depends(get_db)):
    db_v = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if not db_v or not verify_password(vendor.password, db_v.password_hash): raise HTTPException(status_code=401)
    return {"access_token": create_access_token(data={"sub": db_v.email, "id": db_v.id})}

@app.get("/")
async def root(): return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
