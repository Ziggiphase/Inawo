from fastapi import FastAPI, Request, UploadFile, File, Form, Response
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. THE "HEALTH CHECK" FIX
# We accept BOTH GET and HEAD to satisfy Render's load balancer
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "alive", "service": "inawo-ai"}

def extract_text_from_file(file_content: bytes, filename: str) -> str:
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
        return f"Error parsing {filename}: {str(e)}"
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
        final_catalog += f"\n\n[Uploaded Document: {file.filename}]\n{extracted}"

    vendor_data = {"businessName": businessName, "category": category, "catalog": final_catalog}
    
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    return {"status": "success"}

# 2. THE BACKGROUND STARTUP
@app.on_event("startup")
async def startup_event():
    # We add a small sleep to ensure the Web Server port is bound first
    await asyncio.sleep(1) 
    try:
        await bot_app.initialize()
        # Non-blocking background task
        asyncio.create_task(bot_app.updater.start_polling())
        asyncio.create_task(bot_app.start())
        print("✅ Telegram Bot Active")
    except Exception as e:
        print(f"⚠️ Bot Start Warning: {e}")

if __name__ == "__main__":
    import uvicorn
    # Render uses port 10000 by default, but we grab it from the ENV
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
