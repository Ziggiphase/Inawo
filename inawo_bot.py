import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 
from vision_service import extract_receipt_details  # Import our new vision logic
from database import get_db
from models import Sale, ChatSession

load_dotenv()

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from database import get_db
from models import ChatSession, Vendor

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    # 1. Extract the vendor_id from the /start command (e.g., /start 5)
    args = context.args
    db = next(get_db())

    if args:
        vendor_id = int(args[0])
        # 2. Check if vendor exists
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        
        if vendor:
            # 3. Create or Update the ChatSession
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

    await update.message.reply_text("Welcome to Inawo! Please use a vendor's link to start shopping.")

# Add this to your bot_application in inawo_bot.py
# bot_application.add_handler(CommandHandler("start", start))
# --- 1. EXISTING TEXT HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    
    try:
        with open("registry.json", "r") as f:
            vendor_data = json.load(f)
        biz_info = vendor_data.get("knowledgeBase", "No data available.")
        biz_name = vendor_data.get("businessName", "Inawo Vendor")
    except FileNotFoundError:
        biz_info, biz_name = "System active.", "Inawo"

    config = {
        "configurable": {
            "thread_id": chat_id,
            "business_data": f"Business: {biz_name}. Catalog: {biz_info}"
        }
    }

    inputs = {"messages": [("user", user_text)]}
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

# --- 2. NEW PHOTO HANDLER (For Receipts) ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the photo file (highest quality)
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("I see a receipt! Analyzing the transaction... 🧐")

    # Call the vision service
    receipt_data = await extract_receipt_details(bytes(image_bytes))
    
    if "error" in receipt_data:
        await update.message.reply_text("I'm sorry, I couldn't read that clearly. Can you send a sharper photo?")
        return

    # Log to Database (Pending Confirmation)
    db = next(get_db())
    new_sale = Sale(
        amount=float(receipt_data.get('amount', 0)),
        customer_name=update.message.from_user.full_name,
        status="Pending"
    )
    # Note: In production, we'll link this to the specific Vendor ID
    db.add(new_sale)
    db.commit()

    confirmation = (
        f"✅ Found it!\n"
        f"Amount: ₦{receipt_data.get('amount')}\n"
        f"Bank: {receipt_data.get('bank')}\n\n"
        f"I've sent this to the vendor for confirmation."
    )
    await update.message.reply_text(confirmation)

# --- 3. BOT APPLICATION SETUP ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot_application = ApplicationBuilder().token(TOKEN).build()

# Register the photo handler BEFORE or AFTER the text handler
bot_application.add_handler(CommandHandler("start", start))
bot_application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
