import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 

load_dotenv()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    db = next(get_db())
    
    # 1. Look up which vendor this chat belongs to
    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    
    if not session:
        await update.message.reply_text("Please start the chat via a vendor's unique link.")
        return

    # 2. Check if the Vendor is currently "In the Chat" (Manual Mode)
    if session.is_manual_mode:
        # AI stays silent or just logs the message for the dashboard
        return 

    # 3. Get Vendor's specific Knowledge Base
    vendor = db.query(Vendor).filter(Vendor.id == session.vendor_id).first()
    biz_info = vendor.knowledge_base.content if vendor.knowledge_base else "General info"

    # 4. Run AI with this specific vendor's context
    config = {
        "configurable": {
            "thread_id": chat_id,
            "business_data": f"Business: {vendor.business_name}. Catalog: {biz_info}"
        }
    }
    # ... call inawo_app as usual

    inputs = {"messages": [("user", user_text)]}
    
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot_application = ApplicationBuilder().token(TOKEN).build()
bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
