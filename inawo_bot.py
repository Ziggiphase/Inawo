import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 

load_dotenv()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = str(update.message.chat_id)
    
    # Always pull the FRESH PDF data from the registry
    try:
        with open("registry.json", "r") as f:
            vendor_data = json.load(f)
        biz_info = vendor_data.get("knowledgeBase", "No data available.")
        biz_name = vendor_data.get("businessName", "Inawo Vendor")
    except FileNotFoundError:
        biz_info, biz_name = "System active.", "Inawo"

    # We pass the context into the 'configurable' field
    # This prevents the memory saver from 'locking' old business data
    config = {
        "configurable": {
            "thread_id": chat_id,
            "business_data": f"Business: {biz_name}. Catalog: {biz_info}"
        }
    }

    inputs = {"messages": [("user", user_text)]}
    
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot_application = ApplicationBuilder().token(TOKEN).build()
bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
