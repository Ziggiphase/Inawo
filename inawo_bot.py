import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 

load_dotenv()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    try:
        with open("registry.json", "r") as f:
            vendor_data = json.load(f)
        
        biz_name = vendor_data.get("businessName", "Inawo Vendor")
        # FIX: Changed 'catalog' to 'knowledgeBase' to match your registry.json
        biz_info = vendor_data.get("knowledgeBase", "No items listed yet.")
        biz_type = vendor_data.get("category", "General")
        
    except FileNotFoundError:
        biz_name, biz_info, biz_type = "Inawo Assistant", "Service active", "Support"

    inputs = {
        "messages": [("user", user_text)],
        "business_type": f"Business Name: {biz_name}, Category: {biz_type}, Products: {biz_info}" 
    }

    config = {"configurable": {"thread_id": str(update.message.chat_id)}}
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

# We export the app creation so main.py can start it
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot_application = ApplicationBuilder().token(TOKEN).build()
bot_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
