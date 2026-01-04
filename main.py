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

# --- WHATSAPP HANDSHAKE ---

@app.get("/webhook")
@app.get("/webhook/")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    print(f"DEBUG: Comparing Received Token '{token}' with Expected Token '{verify_token}'")

    if mode == "subscribe" and token == verify_token:
        return Response(content=challenge, media_type="text/plain")
    
    return Response(content="Mismatch Error", status_code=403)

@app.post("/webhook")
async def handle_whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        # 1. Standard WhatsApp Parsing
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value")
                    if "messages" in value:
                        message = value["messages"][0]
                        sender_number = message["from"]
                        user_text = message.get("text", {}).get("body", "")

                        # 2. VENDOR LOOKUP (The Multitenant Secret)
                        # We find which vendor this customer is chatting with
                        # (This assumes you have a ChatSession table linking users to vendors)
                        vendor = db.query(models.Vendor).join(models.ChatSession).filter(
                            models.ChatSession.customer_number == sender_number
                        ).first()

                        if not vendor:
                            # Fallback if it's a new customer
                            business_context = "A helpful business assistant."
                        else:
                            # Pull the specific knowledge base for this vendor
                            business_context = vendor.knowledge_base_text 

                        # 3. FEED CONTEXT TO AI
                        # We 'prime' the AI with the vendor's specific identity
                        system_prompt = f"You are the AI assistant for {vendor.business_name if vendor else 'Inawo'}. Use this info: {business_context}"
                        
                        inputs = {"messages": [("system", system_prompt), ("user", user_text)]}
                        config = {"configurable": {"thread_id": sender_number}}
                        
                        result = await inawo_app.ainvoke(inputs, config)
                        ai_reply = result["messages"][-1].content

                        # 4. SEND REPLY
                        await send_whatsapp_message(sender_number, ai_reply)

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Logic Error: {e}")
        return {"status": "error"}

# --- OTHER ROUTES ---

@app.get("/")
async def root():
    return {"status": "Inawo API is running", "engine": "Llama 3.3 70B"}

@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    existing = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_vendor = models.Vendor(
        email=vendor.email,
        business_name=vendor.business_name,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_vendor)
    db.commit()
    return {"status": "success"}

@app.post("/login")
async def login(vendor: VendorSignup, db: Session = Depends(get_db)):
    db_vendor = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if not db_vendor or not verify_password(vendor.password, db_vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": db_vendor.email, "id": db_vendor.id})
    return {"access_token": token}

# --- LIFECYCLE (BOT PAUSED) ---

@app.on_event("startup")
async def startup_event():
    # 1. Prioritize API availability
    print("🚀 Inawo API is active and ready for WhatsApp.")
    
    # 2. Wait 15 seconds to let old Render 'ghost' processes die off
    # This is the secret to avoiding the Telegram 'Conflict' error
    await asyncio.sleep(15)
    
    if bot_application:
        try:
            # 3. Initialize the bot
            await bot_application.initialize()
            
            # Start polling in a background task so it doesn't block the API thread
            # 'drop_pending_updates=True' prevents the bot from spamming you with 
            # old messages that were sent while the bot was paused.
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
            
            print("✅ Telegram Bot is back online and safe!")
        except Exception as e:
            # If a conflict STILL happens, we catch it here so the API stays online
            print(f"⚠️ Telegram Startup Note (API is still running): {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
