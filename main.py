from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
from inawo_bot import bot_application # Import the bot instance

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "Inawo AI is active"}

@app.post("/onboard")
async def onboard_vendor(request: Request):
    vendor_data = await request.json()
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
    return {"status": "success"}

@app.on_event("startup")
async def startup_event():
    # This starts the Telegram bot in the background when FastAPI starts
    print("🚀 Starting Inawo Telegram Bot...")
    await bot_application.initialize()
    asyncio.create_task(bot_application.updater.start_polling())
    asyncio.create_task(bot_application.start())
    print("✅ Bot is listening!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
