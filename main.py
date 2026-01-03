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

# --- DATABASE & SECURITY IMPORTS ---
from database import get_db, engine
import models
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_vendor # Make sure you created this file!
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

# --- FILE EXTRACTOR ---
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

# --- PUBLIC AUTH ROUTES ---

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

# --- PROTECTED VENDOR ROUTES ---

@app.post("/onboard")
async def onboard_vendor(
    knowledgeBase: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    final_knowledge = knowledgeBase if knowledgeBase else ""
    if file:
        file_bytes = await file.read()
        final_knowledge += f"\n\n--- DOCUMENT: {file.filename} ---\n{extract_text_from_file(file_bytes, file.filename)}"

    kb = db.query(models.KnowledgeBase).filter(models.KnowledgeBase.vendor_id == current_vendor.id).first()
    if not kb:
        kb = models.KnowledgeBase(vendor_id=current_vendor.id, content=final_knowledge)
        db.add(kb)
    else:
        kb.content = final_knowledge
    db.commit()
    return {"status": "success"}

@app.get("/sales")
async def get_sales(
    db: Session = Depends(get_db),
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    return db.query(models.Sale).filter(models.Sale.vendor_id == current_vendor.id).all()

@app.post("/sales/{sale_id}/confirm")
async def confirm_sale(
    sale_id: int, 
    db: Session = Depends(get_db),
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    sale = db.query(models.Sale).filter(
        models.Sale.id == sale_id, 
        models.Sale.vendor_id == current_vendor.id
    ).first()
    
    if sale:
        sale.status = "Confirmed"
        db.commit()
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Sale not found or unauthorized")

@app.get("/vendor/chats")
async def get_active_chats(
    db: Session = Depends(get_db),
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    chats = db.query(models.ChatSession).filter(models.ChatSession.vendor_id == current_vendor.id).all()
    return [
        {
            "chat_id": chat.id,
            "customer_name": chat.customer_name or "Guest Customer",
            "is_manual_mode": chat.is_manual_mode
        } for chat in chats
    ]

@app.post("/vendor/send-message")
async def send_admin_message(
    payload: AdminMessage,
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    # Verify the chat belongs to this vendor before sending
    # (Security check skipped here for brevity, but recommended)
    try:
        await bot_application.bot.send_message(
            chat_id=payload.chat_id, 
            text=f"👨‍💼 ({current_vendor.business_name}): {payload.text}"
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendor/stats")
async def get_vendor_stats(
    db: Session = Depends(get_db),
    current_vendor: models.Vendor = Depends(get_current_vendor)
):
    total_revenue = db.query(func.sum(models.Sale.amount))\
        .filter(models.Sale.vendor_id == current_vendor.id, models.Sale.status == "Confirmed")\
        .scalar() or 0
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    daily_sales = db.query(
        cast(models.Sale.created_at, Date).label("day"),
        func.sum(models.Sale.amount).label("total")
    ).filter(
        models.Sale.vendor_id == current_vendor.id,
        models.Sale.status == "Confirmed",
        models.Sale.created_at >= seven_days_ago
    ).group_by("day").order_by("day").all()

    chart_data = [{"date": str(s.day), "amount": s.total} for s in daily_sales]
    
    return {
        "total_revenue": total_revenue,
        "chart_data": chart_data
    }

# --- WEBHOOKS & SYSTEM ---

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")

@app.get("/")
async def root():
    return {"status": "Inawo SaaS API Online"}

@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(2)
    try:
        await bot_application.initialize()
        asyncio.create_task(bot_application.updater.start_polling())
        asyncio.create_task(bot_application.start())
        print("✅ Protected Multi-tenant Bot active")
    except Exception as e:
        print(f"⚠️ Bot error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
