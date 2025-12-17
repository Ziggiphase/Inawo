import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # Safely load the dynamic registry from the portal
    try:
        if os.path.exists("registry.json"):
            with open("registry.json", "r") as f:
                vendor_data = json.load(f)
        else:
            vendor_data = {}
        
        biz_name = vendor_data.get("businessName", "Inawo Vendor")
        biz_info = vendor_data.get("catalog", "Our services")
        biz_type = vendor_data.get("category", "Retail")
    except:
        biz_name, biz_info, biz_type = "Inawo Partner", "General", "Support"

    inputs = {
        "messages": [("user", user_text)],
        "business_type": f"{biz_type} (Name: {biz_name}, Info: {biz_info})" 
    }

    config = {"configurable": {"thread_id": str(chat_id)}}
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

# Initialize the Application object for main.py to use
TOKEN = os.getenv("TELEGRAM_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
