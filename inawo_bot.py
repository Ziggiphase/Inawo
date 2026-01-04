import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from inawo_logic import inawo_app 
from vision_service import extract_receipt_details 
from database import get_db
from models import Sale, ChatSession, Vendor

# --- 1. START COMMAND (Deep Linking) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    args = context.args
    db = next(get_db())

    if args:
        try:
            vendor_id = int(args[0])
            vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
            
            if vendor:
                session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
                if not session:
                    session = ChatSession(id=chat_id, vendor_id=vendor_id)
                    db.add(session)
                else:
                    session.vendor_id = vendor_id
                db.commit()

                await update.message.reply_text(
                    f"Welcome to {vendor.business_name}! 🛍️\n"
                    "I am their AI assistant. How can I help you today?"
                )
                return
        except ValueError:
            pass

    await update.message.reply_text("Welcome to Inawo! Please use a vendor's link to start shopping.")

# --- 2. TEXT MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    
    # Get vendor info from DB based on session
    db = next(get_db())
    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    
    biz_name = "Inawo Vendor"
    biz_info = "Assistant active."
    
    if session:
        vendor = db.query(Vendor).filter(Vendor.id == session.vendor_id).first()
        if vendor:
            biz_name = vendor.business_name
            biz_info = vendor.knowledge_base.content if vendor.knowledge_base else "No catalog uploaded."

    config = {
        "configurable": {
            "thread_id": chat_id,
            "business_data": f"Business: {biz_name}. Catalog: {biz_info}"
        }
    }

    inputs = {"messages": [("user", user_text)]}
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

# --- 3. PHOTO HANDLER ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("I see a receipt! Analyzing... 🧐")
    receipt_data = await extract_receipt_details(bytes(image_bytes))
    
    if "error" in receipt_data:
        await update.message.reply_text("I couldn't read that clearly. Can you send a sharper photo?")
        return

    # Log to Database
    db = next(get_db())
    # Link to vendor from session
    session = db.query(ChatSession).filter(ChatSession.id == str(update.message.chat_id)).first()
    
    new_sale = Sale(
        amount=float(receipt_data.get('amount', 0)),
        customer_name=update.message.from_user.full_name,
        vendor_id=session.vendor_id if session else None,
        status="Pending"
    )
    db.add(new_sale)
    db.commit()

    await update.message.reply_text(f"✅ Found it! ₦{receipt_data.get('amount')}. Sent to vendor.")

# --- 4. INITIALIZATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("⚠️ WARNING: TELEGRAM_TOKEN not found. Bot will not start.")
    bot_application = None
else:
    bot_application = ApplicationBuilder().token(TOKEN).build()
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
