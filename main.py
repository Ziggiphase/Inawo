import os
import json
import asyncio
from io import BytesIO
from typing import List

import pandas as pd
import pdfplumber
import docx
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta

# --- NEW IMPORTS FOR V2 ---
from database import get_db, engine
import models
from security import hash_password, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field

# Initialize Database Tables
models.Base.metadata.create_all(bind=engine)

# Import your bot instance
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHEMAS FOR API ---
class VendorSignup(BaseModel):
    # Step 1: Account
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    # Step 2: Business Profile
    business_name: str
    phone_number: str
    category: str  # e.g., Fashion, Electronics
    
    # Step 3: Payout Info (Bank Details)
    bank_name: str
    account_number: str = Field(..., min_length=10, max_length=10)
    account_name: str

# --- THE EXTRACTOR ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    try:
        stream = BytesIO(file_content)
        if filename.endswith('.csv'):
            return pd.read_csv(stream).to_string()
        elif filename.endswith(('.xls', '.xlsx')):
            return pd.read_excel(stream).to_string()
        elif filename.endswith('.pdf'):
            text_output = []
            with pdfplumber.open(stream) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                text_output.append(" | ".join([str(i).strip() for i in row if i is not None]))
                    page_text = page.extract_text()
                    if page_text: text_output.append(page_text)
            return "\n".join(text_output)
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(stream)
            return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"[Error parsing {filename}: {str(e)}]"
    return ""

# --- AUTH ROUTES ---

@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    # Check if exists
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

# --- VENDOR ONBOARDING & DASHBOARD ROUTES ---

@app.post("/onboard")
async def onboard_vendor(
    vendor_id: int = Form(...),
    knowledgeBase: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    final_knowledge = knowledgeBase if knowledgeBase else ""
    if file:
        file_bytes = await file.read()
        final_knowledge += f"\n\n--- DOCUMENT: {file.filename} ---\n{extract_text_from_file(file_bytes, file.filename)}"

    # Update KnowledgeBase in DB
    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.vendor_id == vendor_id).first()
    if not kb:
        kb = models.KnowledgeBase(vendor_id=vendor_id, content=final_knowledge)
        db.add(kb)
    else:
        kb.content = final_knowledge
    db.commit()
    return {"status": "success"}

@app.post("/chat/{chat_id}/toggle-manual")
async def toggle_manual(chat_id: str, db: Session = Depends(get_db)):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == chat_id).first()
    if not session: raise HTTPException(status_code=404, detail="Chat not found")
    
    session.is_manual_mode = not session.is_manual_mode
    db.commit()
    return {"mode": "Manual" if session.is_manual_mode else "AI"}

@app.get("/sales")
async def get_sales(vendor_id: int, db: Session = Depends(get_db)):
    return db.query(models.Sale).filter(models.Sale.vendor_id == vendor_id).all()

@app.post("/sales/{sale_id}/confirm")
async def confirm_sale(sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(models.Sale).filter(models.Sale.id == sale_id).first()
    if sale:
        sale.status = "Confirmed"
        db.commit()
        return {"status": "success"}
    return {"error": "Not found"}

@app.get("/")
async def root():
    return {"status": "Inawo SaaS API Online"}

# 1. FETCH ALL ACTIVE CHATS FOR A VENDOR
@app.get("/vendor/{vendor_id}/chats")
async def get_active_chats(vendor_id: int, db: Session = Depends(get_db)):
    chats = db.query(models.ChatSession).filter(models.ChatSession.vendor_id == vendor_id).all()
    
    # We return the chat_id and the manual status
    return [
        {
            "chat_id": chat.id,
            "customer_name": chat.customer_name or "Guest Customer",
            "is_manual_mode": chat.is_manual_mode
        } for chat in chats
    ]

# 2. SEND A MANUAL MESSAGE FROM DASHBOARD TO TELEGRAM
class AdminMessage(BaseModel):
    chat_id: str
    text: str

@app.post("/vendor/send-message")
async def send_admin_message(payload: AdminMessage):
    try:
        # This sends a message directly to the Telegram user via your bot
        await bot_application.bot.send_message(
            chat_id=payload.chat_id, 
            text=f"👨‍💼 (Owner): {payload.text}"
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendor/{vendor_id}/stats")
async def get_vendor_stats(vendor_id: int, db: Session = Depends(get_db)):
    # 1. Calculate Total Revenue (Confirmed only)
    total_revenue = db.query(func.sum(models.Sale.amount))\
        .filter(models.Sale.vendor_id == vendor_id, models.Sale.status == "Confirmed")\
        .scalar() or 0
    
    # 2. Daily Sales Data for the last 7 days (for the Chart)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_sales = db.query(
        cast(models.Sale.created_at, Date).label("day"),
        func.sum(models.Sale.amount).label("total")
    ).filter(
        models.Sale.vendor_id == vendor_id,
        models.Sale.status == "Confirmed",
        models.Sale.created_at >= seven_days_ago
    ).group_by("day").order_by("day").all()

    # Format for Recharts (Frontend)
    chart_data = [{"date": str(s.day), "amount": s.total} for s in daily_sales]
    
    return {
        "total_revenue": total_revenue,
        "chart_data": chart_data
    }

# WHATSAPP WEBHOOK VERIFICATION (Needed for Step 1)
@app.get("/webhook")
async def verify_webhook(request: Request):
    # This is a one-time check Meta does to make sure your server is real
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN") # Create a secret string in .env
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")



# --- BOT LIFECYCLE ---
@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(2)
    try:
        await bot_application.initialize()
        asyncio.create_task(bot_application.updater.start_polling())
        asyncio.create_task(bot_application.start())
        print("✅ Multi-tenant Bot active")
    except Exception as e:
        print(f"⚠️ Bot error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
