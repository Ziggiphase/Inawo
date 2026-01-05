import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from inawo_logic import inawo_app 
from vision_service import extract_receipt_details 
from database import SessionLocal
from models import Sale, ChatSession, Vendor

# --- 1. START COMMAND (Unified Vendor & Customer Entry) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    args = context.args # Extracts parameters like 'v_123'
    db = SessionLocal()

    try:
        # CASE A: VENDOR LINKING (From Dashboard)
        if args and args[0].startswith("v_"):
            vendor_id = int(args[0].split("_")[1])
            vendor = db.query(Vendor).get(vendor_id)
            if vendor:
                vendor.telegram_chat_id = chat_id
                db.commit()
                await update.message.reply_text(
                    f"✅ Connection Successful!\n\n{vendor.business_name} is now linked to this Telegram account. "
                    "You will receive instant alerts here whenever a customer places an order or pays on WhatsApp."
                )
                return

        # CASE B: CUSTOMER STARTING CHAT
        elif args:
            try:
                vendor_id = int(args[0])
                vendor = db.query(Vendor).get(vendor_id)
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
            except ValueError:
                pass

        # CASE C: NO ARGUMENTS
        await update.message.reply_text("Welcome to Inawo! Please use a vendor's unique link to start shopping or link your business.")
    
    except Exception as e:
        print(f"⚠️ Bot Start Error: {e}")
    finally:
        db.close()

# --- 2. TEXT MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    db = SessionLocal()
    
    try:
        session = db.query(ChatSession).filter(ChatSession.customer_number == chat_id).first()
        
        # If no session, we don't know which business to represent
        if not session:
            return

        # Check if Human Take-Over is active
        if session.is_ai_paused:
            return 

        vendor = db.query(Vendor).get(session.vendor_id)
        if not vendor:
            return

        # Prepare context for the LangGraph Brain
        config = {
            "configurable": {
                "thread_id": chat_id,
                "business_data": vendor.business_name,
                "knowledge": vendor.knowledge_base_text,
                "out_of_stock": vendor.out_of_stock_items or "None"
            }
        }

        inputs = {"messages": [("user", user_text)]}
        result = await inawo_app.ainvoke(inputs, config)
        
        # Reply with the AI's response
        await update.message.reply_text(result["messages"][-1].content)
        
    except Exception as e:
        print(f"⚠️ Bot Message Error: {e}")
    finally:
        db.close()

# --- 3. PHOTO HANDLER (Payment Receipts) ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    
    await update.message.reply_text("I see a receipt! Checking that for you... 🧐")
    
    # Process with Groq Vision
    receipt_data = await extract_receipt_details(bytes(image_bytes))
    
    if "error" in receipt_data:
        await update.message.reply_text("I couldn't quite read that. Could you send a clearer photo?")
        return

    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.customer_number == chat_id).first()
        if session:
            new_sale = Sale(
                amount=float(receipt_data.get('amount', 0)),
                customer_name=update.message.from_user.full_name or "Telegram User",
                vendor_id=session.vendor_id,
                status="Pending"
            )
            db.add(new_sale)
            db.commit()
            await update.message.reply_text(f"✅ Received! ₦{receipt_data.get('amount')} logged. The vendor has been notified.")
    except Exception as e:
        print(f"⚠️ Photo Logic Error: {e}")
    finally:
        db.close()

# --- 4. INITIALIZATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

if TOKEN:
    bot_application = ApplicationBuilder().token(TOKEN).build()
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
else:
    bot_application = None
    print("⚠️ TELEGRAM_TOKEN not found. Bot functionality disabled.")
