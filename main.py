from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from inawo_bot import app as bot_app  # Ensure your bot instance is named 'app'

app = FastAPI()

# 1. CORS Setup for Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/onboard")
async def onboard_vendor(request: Request):
    vendor_data = await request.json()
    
    # Save the vendor's data to registry.json
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"New Vendor Registered: {vendor_data.get('businessName')}")
    return {"status": "success", "message": "Inawo AI is now active!"}

# --- THE NEW UPDATE: STARTUP HOOK ---

@app.on_event("startup")
async def startup_event():
    """
    This function runs when FastAPI starts. 
    It launches the Telegram bot in the background so they share the same event loop.
    """
    print("Launching Inawo Telegram Bot in background...")
    # We initialize the bot and start polling without blocking FastAPI
    asyncio.create_task(bot_app.initialize())
    asyncio.create_task(bot_app.updater.start_polling())
    asyncio.create_task(bot_app.start())

if __name__ == "__main__":
    import uvicorn
    # We run on port 8000 as required by Render
    uvicorn.run(app, host="0.0.0.0", port=8000)
