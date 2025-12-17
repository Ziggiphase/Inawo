from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import pandas as pd
import pdfplumber
import docx
from io import BytesIO
import os
from inawo_bot import app as bot_app

app = FastAPI()

# 1. CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. THE STAY-ALIVE ROUTE (Fixes the 404 shutdown)
@app.get("/")
async def root():
    return {
        "status": "Inawo API is running",
        "bot_status": "active",
        "message": "Ready for onboarding"
    }

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Helper function to extract text based on file type."""
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(file_content))
            return df.to_string()
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(BytesIO(file_content))
            return df.to_string()
        elif filename.endswith('.pdf'):
            with pdfplumber.open(BytesIO(file_content)) as pdf:
                return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(BytesIO(file_content))
            return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"Error parsing file: {str(e)}"
    return ""

@app.post("/onboard")
async def onboard_vendor(
    businessName: str = Form(...),
    category: str = Form(...),
    catalog_text: str = Form(None),
    file: UploadFile = File(None)
):
    final_catalog = catalog_text if catalog_text else ""

    if file:
        content = await file.read()
        extracted = extract_text_from_file(content, file.filename)
        final_catalog += f"\n\n[Content from {file.filename}]:\n{extracted}"

    vendor_data = {
        "businessName": businessName,
        "category": category,
        "catalog": final_catalog
    }
    
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"✅ Onboarded {businessName} with catalog data.")
    return {"status": "success", "message": "Inawo AI is now trained!"}

# 3. SECURE STARTUP HOOK
@app.on_event("startup")
async def startup_event():
    print("🚀 System Booting...")
    try:
        await bot_app.initialize()
        # Background tasks to prevent blocking the web server
        asyncio.create_task(bot_app.updater.start_polling())
        asyncio.create_task(bot_app.start())
        print("✅ Telegram Bot is listening.")
    except Exception as e:
        print(f"❌ Bot Startup Error: {e}")
    print("✅ Web Server Online.")

if __name__ == "__main__":
    import uvicorn
    # Important: Use the PORT environment variable for Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
