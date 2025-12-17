import os
import json
import asyncio
from io import BytesIO

# 1. NEW IMPORTS FOR FILE PROCESSING
import pandas as pd
import pdfplumber
import docx
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# Import your bot instance
from inawo_bot import bot_application

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE EXTRACTOR (How we turn files into AI context) ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Helper function to extract text based on file type."""
    try:
        # We use BytesIO to read the file in memory without saving it to disk
        stream = BytesIO(file_content)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(stream)
            return df.to_string()
        
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(stream)
            return df.to_string()
        
        elif filename.endswith('.pdf'):
            with pdfplumber.open(stream) as pdf:
                # Extract text from every page
                return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(stream)
            return "\n".join([para.text for para in doc.paragraphs])
            
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return f"[Error: Could not read content from {filename}]"
    
    return ""

# --- THE ONBOARD ROUTE (The core of the SaaS) ---
@app.post("/onboard")
async def onboard_vendor(
    businessName: str = Form(...),
    category: str = Form(...),
    knowledgeBase: str = Form(None),
    file: UploadFile = File(None)
):
    # 1. Get the manual text if any
    final_knowledge = knowledgeBase if knowledgeBase else ""

    # 2. Extract file content if a file was uploaded
    if file:
        file_bytes = await file.read()
        extracted_text = extract_text_from_file(file_bytes, file.filename)
        # We append the file text to the manual text
        final_knowledge += f"\n\n--- DOCUMENT CONTENT ({file.filename}) ---\n{extracted_text}"

    # 3. Create the data structure for registry.json
    vendor_data = {
        "businessName": businessName,
        "category": category,
        "knowledgeBase": final_knowledge
    }
    
    # 4. Save to the shared JSON file
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"✅ Onboarded: {businessName}")
    return {"status": "success", "message": "Inawo AI is now trained!"}

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Inawo API is running"}

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Telegram Bot Task...")
    await bot_application.initialize()
    asyncio.create_task(bot_application.updater.start_polling())
    asyncio.create_task(bot_application.start())
    print("✅ Bot is online.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
