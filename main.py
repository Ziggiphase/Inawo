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

# Build DB Tables automatically
models.Base.metadata.create_all(bind=engine)
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS (Expanded to match Lovable Frontend) ---
class VendorSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str
    category: str = "General"
    bank_name: str = None
    account_number: str = None
    account_name: str = None

class InventoryUpdate(BaseModel):
    items: str

# --- ROOT ROUTE (Render Health Check) ---
@app.get("/")
async def root():
    return {"status": "Inawo API Active", "version": "1.0.0", "engine": "Llama 3.3 70B"}

# --- AUTH ROUTES ---
@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    existing = db.query(models.Vendor).filter(models.Vendor.email == vendor.email).first()
    if existing: 
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_v = models.Vendor(
        email=vendor.email, 
        business_name=vendor.business_name, 
        phone_number=vendor.phone_number,
        category=vendor.category,
        bank_name=vendor.bank_name,
        account_number=vendor.account_number,
        account_name=vendor.account_name,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_v)
    db.commit()
    return {"status": "success"}

@app.post("/login")
async def login(v: VendorSignup, db: Session = Depends(get_db)):
    user = db.query(models.Vendor).filter(models.Vendor.email == v.email).first()
    if not user or not verify_password(v.password, user.password_hash): 
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user.email, "id": user.id})
    return {"access_token": token, "token_type": "bearer"}

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

                        # 1. AUTO-SESSION / VENDOR LINKING
                        session = db.query(models.ChatSession).filter(models.ChatSession.customer_number == sender).first()
                        if not session:
                            vendor = db.query(models.Vendor).first()
                            if not vendor: return {"status": "no_vendor"}
                            session = models.ChatSession(customer_number=sender, vendor_id=vendor.id)
                            db.add(session); db.commit()

                        vendor = db.query(models.Vendor).get(session.vendor_id)

                        # 2. IMAGE HANDLER (Payment Logic)
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

                        # 3. TEXT HANDLER (AI Brain + Order Extraction)
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender, content=text, role="user"))
                            
                            # AI Reply
                            prompt = f"Concise AI for {vendor.business_name}. {vendor.knowledge_base_text}. STOCK: {vendor.out_of_stock_items}. Max 2 sentences."
                            result = await inawo_app.ainvoke({"messages": [("system", prompt), ("user", text)]}, {"configurable": {"thread_id": sender}})
                            reply = result["messages"][-1].content
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender="AI", content=reply, role="assistant"))
                            db.commit()
                            await send_whatsapp_message(sender, reply)

                            # Order Extraction
                            ext_p = f"Extract order from: '{text}'. Return ONLY JSON: {{\"item\": str, \"total\": float}} or null."
                            ext = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext["messages"][-1].content)
                                if o_data and o_data.get("item"):
                                    db.add(models.Order(vendor_id=vendor.id, customer_number=sender, items=o_data['item'], amount=o_data.get('total', 0)))
                                    db.commit()
                            except: pass
        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Crash: {e}")
        return {"status": "error"}

# --- VENDOR DASHBOARD ROUTES ---
@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success"}

@app.get("/vendor/stats")
async def get_stats(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    results = db.query(cast(models.Order.created_at, Date).label("day"), func.sum(models.Order.amount).label("total")).filter(models.Order.vendor_id == curr.id).group_by(cast(models.Order.created_at, Date)).all()
    return [{"day": str(r.day), "total": r.total} for r in results]

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).order_by(models.Order.created_at.desc()).all()

# --- LIFECYCLE ---
@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
            print("✅ Telegram Polling Started")
        except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
