import os
import json
import asyncio
from io import BytesIO

# 1. Imports for File Processing
import pandas as pd
import pdfplumber
import docx
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# Import your bot instance
from inawo_bot import bot_application

# --- INITIALIZE THE APP (Render looks for this 'app' variable) ---
app = FastAPI(title="Inawo AI Backend")

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE ENHANCED EXTRACTOR (Table-Aware PDF parsing) ---
def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Helper function to extract text based on file type with table support."""
    try:
        stream = BytesIO(file_content)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(stream)
            return df.to_string()
        
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(stream)
            return df.to_string()
        
        elif filename.endswith('.pdf'):
            text_output = []
            with pdfplumber.open(stream) as pdf:
                for page in pdf.pages:
                    # 1. Extract tables (Best for catalogs and price lists)
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                # Join columns with pipes to help Llama understand the structure
                                clean_row = " | ".join([str(i).strip() for i in row if i is not None])
                                text_output.append(clean_row)
                    
                    # 2. Extract regular text
                    page_text = page.extract_text()
                    if page_text:
                        text_output.append(page_text)
            
            return "\n".join(text_output)
        
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(stream)
            return "\n".join([para.text for para in doc.paragraphs])
            
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return f"[Error: Could not read content from {filename}: {str(e)}]"
    
    return ""

# --- ROUTES ---

@app.post("/onboard")
async def onboard_vendor(
    businessName: str = Form(...),
    category: str = Form(...),
    knowledgeBase: str = Form(None),
    file: UploadFile = File(None)
):
    # Get the manual text input if any
    final_knowledge = knowledgeBase if knowledgeBase else ""

    # Extract file content if a file was uploaded
    if file:
        file_bytes = await file.read()
        extracted_text = extract_text_from_file(file_bytes, file.filename)
        # Append the extracted text to the vendor's context
        final_knowledge += f"\n\n--- DOCUMENT CONTENT ({file.filename}) ---\n{extracted_text}"

    # Prepare data for registry.json
    vendor_data = {
        "businessName": businessName,
        "category": category,
        "knowledgeBase": final_knowledge
    }
    
    # Save to the JSON file
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"✅ Successfully Onboarded: {businessName}")
    return {"status": "success", "message": f"Inawo AI is now trained for {businessName}!"}

@app.get("/")
@app.head("/")
async def root():
    return {"status": "Inawo API is running", "engine": "Llama 3.3 70B"}

# --- BOT LIFECYCLE MANAGEMENT ---
@app.on_event("startup")
async def startup_event():
    print("🚀 System Booting...")
    # Delay to prevent port conflicts on Render restarts
    await asyncio.sleep(2) 
    try:
        await bot_application.initialize()
        # Start the bot as a background task
        asyncio.create_task(bot_application.updater.start_polling())
        asyncio.create_task(bot_application.start())
        print("✅ Telegram Bot is listening!")
    except Exception as e:
        print(f"⚠️ Bot startup error (server will still run): {e}")

# --- LOCAL RUN CONFIG ---
if __name__ == "__main__":
    import uvicorn
    # Use Render's assigned port or default to 10000
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
