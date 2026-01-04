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

class InventoryUpdate(BaseModel):
    items: str # Comma-separated list of out-of-stock items

# --- HELPER: VENDOR ALERTS ---
async def notify_vendor(vendor_id: int, message: str, db: Session):
    vendor = db.query(models.Vendor).get(vendor_id)
    if vendor and vendor.telegram_chat_id and bot_application:
        try:
            await bot_application.bot.send_message(chat_id=vendor.telegram_chat_id, text=f"🔔 INAWO ALERT:\n{message}")
        except: pass

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

                        # 1. HANDLE IMAGES (Receipts)
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
                                    await send_whatsapp_message(sender, f"✅ Payment of ₦{amt} verified!")
                                    await notify_vendor(vendor.id, f"💰 PAID: Order from {sender} (₦{amt})", db)
                            return {"status": "success"}

                        # 2. HANDLE TEXT (Concise AI + Stock Awareness)
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            db.add(models.ChatMessage(vendor_id=vendor.id, sender=sender, content=text, role="user"))
                            
                            # The AI Brain with Stock Awareness
                            prompt = f"""You are the concise AI for {vendor.business_name}. 
                            PRICES: {vendor.knowledge_base_text}. 
                            OUT OF STOCK: {vendor.out_of_stock_items or 'None'}.
                            RULES: Max 2 sentences. If item is out of stock, suggest an alternative."""
                            
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

# --- INVENTORY & DASHBOARD ROUTES ---

@app.post("/vendor/inventory")
async def update_inventory(data: InventoryUpdate, db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    """Allows vendor to set items as out of stock."""
    curr.out_of_stock_items = data.items
    db.commit()
    return {"status": "success", "out_of_stock": data.items}

@app.get("/vendor/stats")
async def get_stats(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    results = db.query(cast(models.Order.created_at, Date).label("day"), func.sum(models.Order.amount).label("total")).filter(models.Order.vendor_id == curr.id).group_by(cast(models.Order.created_at, Date)).all()
    return [{"day": str(r.day), "total": r.total} for r in results]

@app.get("/vendor/orders")
async def get_orders(db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    return db.query(models.Order).filter(models.Order.vendor_id == curr.id).order_by(models.Order.created_at.desc()).all()

@app.post("/upload-knowledge")
async def upload_kb(file: UploadFile = File(...), db: Session = Depends(get_db), curr: models.Vendor = Depends(get_current_vendor)):
    if file.filename.lower().endswith(".pdf"):
        with pdfplumber.open(file.file) as pdf:
            curr.knowledge_base_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            db.commit()
            return {"status": "success"}
    raise HTTPException(status_code=400, detail="Only PDFs supported currently")

# --- AUTH & STARTUP ---
@app.post("/signup")
async def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    db.add(models.Vendor(email=vendor.email, business_name=vendor.business_name, password_hash=hash_password(vendor.password)))
    db.commit(); return {"status": "success"}

@app.post("/login")
async def login(v: VendorSignup, db: Session = Depends(get_db)):
    user = db.query(models.Vendor).filter(models.Vendor.email == v.email).first()
    if not user or not verify_password(v.password, user.password_hash): raise HTTPException(status_code=401)
    return {"access_token": create_access_token(data={"sub": user.email, "id": user.id})}

@app.on_event("startup")
async def startup_event():
    await asyncio.sleep(15)
    if bot_application:
        try:
            await bot_application.initialize()
            asyncio.create_task(bot_application.updater.start_polling(drop_pending_updates=True))
            asyncio.create_task(bot_application.start())
        except: pass

@app.get("/")
async def root(): return {"status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
