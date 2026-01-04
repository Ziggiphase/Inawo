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

# --- SCHEMAS ---
class VendorSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str

class InventoryUpdate(BaseModel):
    items: str

# --- ROUTES ---

@app.get("/")
async def root():
    return {"status": "Inawo API Active", "time": datetime.now(timezone.utc)}

@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    existing = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if existing: raise HTTPException(status_code=400, detail="Email exists")
    new_v = models.Vendor(
        email=vendor.email, 
        business_name=vendor.business_name, 
        phone_number=vendor.phone_number,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_v); db.commit()
    return {"status": "success"}

@app.post("/login")
async def login(v: VendorSignup, db: Session = Depends(get_db)):
    user = db.query(models.Vendor).filter(models.Vendor.email == v.email).first()
    if not user or not verify_password(v.password, user.password_hash): raise HTTPException(status_code=401)
    token = create_access_token(data={"sub": user.email, "id": user.id})
    return {"access_token": token}

# --- WHATSAPP WEBHOOK (With Auto-Session Creation) ---

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
                        
                        # 1. AUTO-SESSION LOGIC
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session:
                            # For testing, we link new customers to the FIRST vendor in the DB
                            first_vendor = db.query(models.Vendor).first()
                            if not first_vendor: return {"status": "no_vendors_in_db"}
                            session = models.ChatSession(customer_number=sender, vendor_id=first_vendor.id)
                            db.add(session); db.commit()

                        if session.is_ai_paused: return {"status": "paused"}
                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # 2. IMAGE HANDLER
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            if "amount" in receipt:
                                order = db.query(models.Order).filter(models.Order.customer_number == sender, models.Order.status == "pending").first()
                                if order:
                                    order.status = "paid"; db.commit()
                                    await send_whatsapp_message(sender, f"✅ Payment of ₦{receipt['amount']} verified!")
                            return {"status": "success"}

                        # 3. TEXT HANDLER
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            prompt = f"Concise AI for {vendor.business_name}. {vendor.knowledge_base_text}. Max 2 sentences."
                            result = await inawo_app.ainvoke({"messages": [("system", prompt), ("user", text)]}, {"configurable": {"thread_id": sender}})
                            reply = result["messages"][-1].content
                            await send_whatsapp_message(sender, reply)
        return {"status": "success"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}

# --- STARTUP ---
@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
            print("✅ Telegram Active")
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
