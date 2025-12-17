import os
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from inawo_logic import inawo_app 

load_dotenv()

# --- STEP 1: DEFINE THE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    try:
        with open("registry.json", "r") as f:
            vendor_data = json.load(f)
        
        biz_name = vendor_data.get("businessName", "Inawo Vendor")
        biz_info = vendor_data.get("catalog", "General items")
        biz_type = vendor_data.get("category", "General")
        print(f"--- Processing for {biz_name} ({biz_type}) ---")
        
    except FileNotFoundError:
        biz_name, biz_info, biz_type = "Inawo Assistant", "Onboarding required", "Support"

    inputs = {
        "messages": [("user", user_text)],
        "business_type": f"{biz_type} (Name: {biz_name}, Info: {biz_info})" 
    }

    config = {"configurable": {"thread_id": str(update.message.chat_id)}}
    result = await inawo_app.ainvoke(inputs, config)
    await update.message.reply_text(result["messages"][-1].content)

# --- STEP 2: INITIALIZE THE APP VARIABLE ---
# This is what main.py imports!
TOKEN = os.getenv("TELEGRAM_TOKEN")
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Note: We removed the 'run_polling' block entirely. 
# FastAPI will call this now.
