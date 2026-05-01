import os
import json
import asyncio
from dotenv import load_dotenv
load_dotenv() # Load .env variables before anything else!

from typing import List
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timezone

# --- INTERNAL IMPORTS ---
from database import get_db, engine
import models
from models import Business, ChatSession, ChatMessage, Order, SenderRole
from security import hash_password, verify_password, create_access_token
from dependencies import get_current_business
from pydantic import BaseModel
from auth_routes import router as auth_router
from api_analytics import router as analytics_router
from api_catalog import router as catalog_router
from api_public import router as public_router

# --- AI & MESSAGING SERVICES ---
from whatsapp_service import send_whatsapp_message, get_whatsapp_media_bytes
from vision_service import extract_receipt_details
from inawo_logic import inawo_app

# 1. Initialize Database Tables
models.Base.metadata.create_all(bind=engine)

# 2. Import Bot Application
from inawo_bot import bot_application

app = FastAPI(title="Inawo AI SaaS")

# 3. Middleware & Routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(catalog_router)
app.include_router(public_router)

class InventoryUpdate(BaseModel):
    items: str

# --- HEALTH CHECK ---
@app.get("/")
async def root():
    return {"status": "Inawo API Active", "engine": "Llama 3.3 70B", "time": datetime.now(timezone.utc)}

# --- WHATSAPP WEBHOOK (The Engine) ---
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

                        # A. Auto-Session Logic
                        session = db.query(ChatSession).filter(ChatSession.customer_phone == sender).first()
                        if not session:
                            business = db.query(Business).first() # Fallback to first business if not specified
                            if not business: return {"status": "no_business"}
                            session = ChatSession(customer_phone=sender, business_id=business.id)
                            db.add(session); db.commit()

                        business = db.query(Business).get(session.business_id)

                        # B. Image/Receipt Processing (Bypasses AI logic usually)
                        if msg.get("type") == "image":
                            media_id = msg["image"]["id"]
                            img_bytes = await get_whatsapp_media_bytes(media_id)
                            receipt = await extract_receipt_details(img_bytes)
                            
                            if "amount" in receipt and not receipt.get("error"):
                                order = db.query(Order).filter(
                                    Order.customer_phone == sender, 
                                    Order.status == "pending"
                                ).order_by(Order.created_at.desc()).first()
                                
                                if order:
                                    order.status = "paid"
                                    db.commit()
                                    await send_whatsapp_message(sender, f"✅ Receipt for ₦{receipt['amount']} verified! Your order is being processed.")
                            return {"status": "success"}

                        # C. Text Message Logic
                        elif msg.get("type") == "text":
                            text = msg["text"]["body"]
                            
                            # 1. Log incoming message (from USER)
                            user_msg = ChatMessage(session_id=session.id, sender_role=SenderRole.USER.value, content=text)
                            db.add(user_msg); db.commit()
                            
                            # 2. Check the "Kill Switch" (Human Handoff)
                            if not business.is_ai_active or session.is_ai_paused:
                                # Do nothing; the owner will reply via dashboard
                                print(f"AI Paused for session {session.id}. Waiting for owner.")
                                return {"status": "success"}

                            # 3. AI Processing (LangGraph)
                            config = {
                                "configurable": {
                                    "thread_id": sender,
                                    "business_data": business.business_name,
                                    "knowledge": business.knowledge_base_text,
                                    "out_of_stock": "None" # Update logic here later based on Product table
                                }
                            }
                            
                            result = await inawo_app.ainvoke({"messages": [("user", text)]}, config)
                            reply = result["messages"][-1].content
                            
                            # 4. Log AI response
                            ai_msg = ChatMessage(session_id=session.id, sender_role=SenderRole.AI.value, content=reply)
                            db.add(ai_msg); db.commit()
                            
                            await send_whatsapp_message(sender, reply)

                            # 5. Automated Order Creation extraction
                            ext_p = f"Extract from: '{text}'. If purchase intent, return JSON: {{\"item\": str, \"total\": float}}. Else return null."
                            ext_res = await inawo_app.ainvoke([("system", ext_p)])
                            try:
                                o_data = json.loads(ext_res["messages"][-1].content)
                                if o_data and o_data.get("item"):
                                    new_order = Order(
                                        business_id=business.id, 
                                        customer_phone=sender, 
                                        items={"item": o_data['item']}, 
                                        total_amount=o_data.get('total', 0)
                                    )
                                    db.add(new_order); db.commit()
                            except: pass

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Webhook Logic Error: {e}")
        return {"status": "error"}

# --- SAFE STARTUP (Render Support) ---
@app.on_event("startup")
async def startup_event():
    async def delayed_bot_start():
        await asyncio.sleep(45) 
        if bot_application:
            try:
                await bot_application.initialize()
                try: await bot_application.updater.stop()
                except: pass
                
                await bot_application.updater.start_polling(drop_pending_updates=True)
                await bot_application.start()
                print("✅ Telegram Polling Active")
            except Exception as e:
                print(f"❌ Bot Startup Failure: {e}")

    asyncio.create_task(delayed_bot_start())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
