import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from inawo_logic import inawo_app 
from vision_service import extract_receipt_details 
from database import SessionLocal # Use SessionLocal for direct DB access
from models import Sale, ChatSession, Vendor

# --- 1. START COMMAND (Updated with Deep Linking) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    args = context.args # Gets the 'v_123' from the link
    db = SessionLocal()

    try:
        # Check if this is a Vendor linking their account
        if args and args[0].startswith("v_"):
            vendor_id = int(args[0].split("_")[1])
            vendor = db.query(Vendor).get(vendor_id)
            if vendor:
                vendor.telegram_chat_id = chat_id
                db.commit()
                await update.message.reply_text(f"✅ Linked! You will now receive instant order alerts for {vendor.business_name}.")
                return
            
        # Standard Customer Start
        elif args:
            vendor_id = int(args[0])
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            if vendor:
                session = db.query(ChatSession).filter(ChatSession.customer_number == chat_id).first()
                if not session:
                    session = ChatSession(customer_number=chat_id, vendor_id=vendor_id)
                    db.add(session)
                else:
                    session.vendor_id = vendor_id
                db.commit()

                await update.message.reply_text(
                    f"Welcome to {vendor.business_name}! 🛍️\n"
                    "I am their AI assistant. How can I help you today?"
                )
                return
    except Exception as e:
        print(f"Bot Start Error: {e}")
    finally:
        db.close()

    await update.message.reply_text("Welcome to Inawo! Please use your vendor's link to start shopping.")

# --- 2. TEXT MESSAGE HANDLER (Concise logic) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    db = SessionLocal()
    
    try:
        session = db.query(ChatSession).filter(ChatSession.customer_number == chat_id).first()
        if session and session.is_ai_paused:
            return # Silent if vendor took over

        vendor = db.query(Vendor).get(session.vendor_id) if session else None
        biz_name = vendor.business_name if vendor else "Inawo Vendor"
        kb = vendor.knowledge_base_text if vendor else "Assistant active."

        system_prompt = f"You are a concise assistant for {biz_name}. Use: {kb}. Max 2 sentences."
        inputs = {"messages": [("system", system_prompt), ("user", user_text)]}
        result = await inawo_app.ainvoke(inputs, {"configurable": {"thread_id": chat_id}})
        
        await update.message.reply_text(result["messages"][-1].content)
    finally:
        db.close()

# --- 3. PHOTO HANDLER ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    await update.message.reply_text("Analyzing receipt... 🧐")
    
    receipt_data = await extract_receipt_details(bytes(image_bytes))
    if "error" in receipt_data:
        await update.message.reply_text("I couldn't read that. Try a sharper photo!")
        return

    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.customer_number == str(update.message.chat_id)).first()
        new_sale = Sale(
            amount=float(receipt_data.get('amount', 0)),
            customer_name=update.message.from_user.full_name,
            vendor_id=session.vendor_id if session else None,
            status="Pending"
        )
        db.add(new_sale)
        db.commit()
        await update.message.reply_text(f"✅ Receipt logged: ₦{receipt_data.get('amount')}.")
    finally:
        db.close()

# --- 4. INITIALIZATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    bot_application = None
else:
    bot_application = ApplicationBuilder().token(TOKEN).build()
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
