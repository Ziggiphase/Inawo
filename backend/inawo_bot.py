import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from inawo_logic import inawo_app 
from vision_service import extract_receipt_details 
from database import SessionLocal
from models import Order, ChatSession, Business, SenderRole

# --- 1. START COMMAND (Unified Business & Customer Entry) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    args = context.args # Extracts parameters like 'v_123'
    db = SessionLocal()

    try:
        # CASE A: BUSINESS LINKING (From Dashboard)
        if args and args[0].startswith("b_"):
            business_id = int(args[0].split("_")[1])
            business = db.query(Business).get(business_id)
            if business:
                business.telegram_chat_id = chat_id
                db.commit()
                await update.message.reply_text(
                    f"✅ Connection Successful!\n\n{business.business_name} is now linked to this Telegram account. "
                    "You will receive instant alerts here whenever a customer places an order or pays on WhatsApp/Telegram."
                )
                return

        # CASE B: CUSTOMER STARTING CHAT
        elif args:
            try:
                business_id = int(args[0])
                business = db.query(Business).get(business_id)
                if business:
                    session = db.query(ChatSession).filter(ChatSession.customer_phone == chat_id).first()
                    if not session:
                        session = ChatSession(customer_phone=chat_id, business_id=business_id)
                        db.add(session)
                    else:
                        session.business_id = business_id
                    db.commit()

                    await update.message.reply_text(
                        f"Welcome to {business.business_name}! 🛍️\n"
                        "I am their AI assistant. How can I help you today?"
                    )
                    return
            except ValueError:
                pass

        # CASE C: NO ARGUMENTS
        await update.message.reply_text("Welcome to Inawo! Please use a business's unique link to start shopping or link your business.")
    
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
        session = db.query(ChatSession).filter(ChatSession.customer_phone == chat_id).first()
        
        # If no session, we don't know which business to represent
        if not session:
            return

        business = db.query(Business).get(session.business_id)
        if not business:
            return

        # Check if Human Take-Over is active
        if not business.is_ai_active or session.is_ai_paused:
            return 

        # Prepare context for the LangGraph Brain
        config = {
            "configurable": {
                "thread_id": chat_id,
                "business_data": business.business_name,
                "knowledge": business.knowledge_base_text,
                "out_of_stock": "None"
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
        session = db.query(ChatSession).filter(ChatSession.customer_phone == chat_id).first()
        if session:
            # We must use Order model
            new_order = Order(
                business_id=session.business_id,
                customer_phone=chat_id,
                items={"extracted_from_receipt": True},
                total_amount=float(receipt_data.get('amount', 0)),
                status="paid"
            )
            db.add(new_order)
            db.commit()
            await update.message.reply_text(f"✅ Received! ₦{receipt_data.get('amount')} logged. The business has been notified.")
    except Exception as e:
        print(f"⚠️ Photo Logic Error: {e}")
    finally:
        db.close()

# --- 4. INITIALIZATION ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TOKEN and TOKEN != "dummy_telegram":
    bot_application = ApplicationBuilder().token(TOKEN).build()
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
else:
    bot_application = None
    print("⚠️ TELEGRAM_BOT_TOKEN not configured correctly. Bot functionality disabled.")
