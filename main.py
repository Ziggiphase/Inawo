from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
import pandas as pd
import pdfplumber
import docx
from io import BytesIO
from inawo_bot import bot_application

app = FastAPI()

# 1. CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE EXTRACTOR FUNCTION ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Processes bytes into a readable string based on file extension."""
    try:
        # Convert bytes to a file-like object in memory
        stream = BytesIO(file_content)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(stream)
            return df.to_string()
        
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(stream)
            return df.to_string()
        
        elif filename.endswith('.pdf'):
            with pdfplumber.open(stream) as pdf:
                # Loop through pages and grab text
                return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(stream)
            return "\n".join([para.text for para in doc.paragraphs])
            
    except Exception as e:
        print(f"Parsing error: {e}")
        return f"[Error parsing file {filename}]"
    
    return ""

# --- THE UPDATED ONBOARD ROUTE ---
@app.post("/onboard")
async def onboard_vendor(
    businessName: str = Form(...),
    category: str = Form(...),
    knowledgeBase: str = Form(None),
    file: UploadFile = File(None)
):
    """
    This route now handles 'Multipart' data. 
    It takes text from the form AND extracts text from the uploaded file.
    """
    # 1. Start with the manual text entered in the textarea
    final_knowledge = knowledgeBase if knowledgeBase else ""

    # 2. If a file was uploaded, extract its content
    if file:
        file_bytes = await file.read()
        extracted_text = extract_text_from_file(file_bytes, file.filename)
        # Combine manual text + file text
        final_knowledge += f"\n\n[Content from {file.filename}]:\n{extracted_text}"

    # 3. Save the combined data to your local registry
    vendor_data = {
        "businessName": businessName,
        "category": category,
        "knowledgeBase": final_knowledge
    }
    
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"✅ Onboarded {businessName}. Data length: {len(final_knowledge)} chars.")
    return {"status": "success", "message": "Inawo AI updated!"}

# --- THE ROOT & STARTUP ---
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "Inawo API is running"}

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Bot...")
    await bot_application.initialize()
    asyncio.create_task(bot_application.updater.start_polling())
    asyncio.create_task(bot_application.start())
    print("✅ Bot Listening.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
