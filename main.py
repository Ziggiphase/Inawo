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
# Import auth_routes if you want to use it, but for now we keep them in main to avoid 404s
# from auth_routes import router as auth_router 

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

class AdminMessage(BaseModel):
    chat_id: str
    text: str

# --- WHATSAPP HANDSHAKE (THE FIX) ---

@app.get("/webhook")
@app.get("/webhook/") # This handles the trailing slash issue
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    # Debugging logs in Render
    print(f"WEBHOOK_DEBUG: Received mode={mode}, token={token}")
    
    if mode == "subscribe" and token == verify_token:
        print("WEBHOOK_DEBUG: Verification Successful!")
        return Response(content=challenge, media_type="text/plain")
    
    print("WEBHOOK_DEBUG: Verification Failed. Token mismatch.")
    return Response(content="Verification failed", status_code=403)

@app.post("/webhook")
@app.post("/webhook/")
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

                        if message.get("type") == "image":
                            media_id = message["image"]["id"]
                            await send_whatsapp_message(sender_number, "Receipt received! Analyzing... 🧐")
                            image_bytes = await get_whatsapp_media_bytes(media_id)
                            if image_bytes:
                                receipt_data = await extract_receipt_details(image_bytes)
                                confirmation = f"✅ Analysis Complete!\nAmount: ₦{receipt_data.get('amount')}\nBank: {receipt_data.get('bank')}"
                                await send_whatsapp_message(sender_number, confirmation)

                        elif message.get("type") == "text":
                            user_text = message["text"]["body"]
                            inputs = {"messages": [("user", user_text)]}
                            config = {"configurable": {"thread_id": sender_number}}
                            result = await inawo_app.ainvoke(inputs, config)
                            ai_reply = result["messages"][-1].content
                            await send_whatsapp_message(sender_number, ai_reply)

        return {"status": "success"}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}

# --- OTHER ROUTES ---

@app.get("/")
async def root():
    return {"status": "Inawo API is running", "engine": "Llama 3.3 70B"}

# [Rest of your signup, login, sales, stats routes here...]
# Ensure you keep the signup/login routes from your previous main.py here

@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    existing = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_vendor = models.Vendor(
        email=vendor.email,
        business_name=vendor.business_name,
        phone_number=vendor.phone_number,
        category=vendor.category,
        bank_name=vendor.bank_name,
        account_number=vendor.account_number,
        account_name=vendor.account_name,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_vendor)
    db.commit()
    return {"status": "success", "message": "Professional profile created!"}

@app.post("/login")
async def login(vendor: VendorSignup, db: Session = Depends(get_db)):
    db_vendor = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if not db_vendor or not verify_password(vendor.password, db_vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": db_vendor.email, "id": db_vendor.id})
    return {"access_token": token, "business_name": db_vendor.business_name}

# --- STARTUP ---
# --- BOT LIFECYCLE ---
# --- BOT LIFECYCLE ---
@app.on_event("startup")
async def startup_event():
    # 1. Give the "Old" Render process 5 seconds to die off
    await asyncio.sleep(5)
    
    if bot_application:
        try:
            # 2. We initialize and start polling in a safe way
            await bot_application.initialize()
            
            # Use a background task so this doesn't block the main thread
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
            
            print("✅ Multi-tenant Bot active")
        except Exception as e:
            # 3. If a conflict occurs, we ONLY log it. 
            # The FastAPI server (and your /webhook) will STAY LIVE.
            print(f"⚠️ Telegram Bot Startup: {e}")
            print("👉 API remains online for WhatsApp/Dashboard logic.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
