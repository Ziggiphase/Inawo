from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from inawo_bot import app as bot_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/onboard")
async def onboard_vendor(request: Request):
    vendor_data = await request.json()
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
    print(f"✅ Onboarded: {vendor_data.get('businessName')}")
    return {"status": "success"}

@app.on_event("startup")
async def startup_event():
    print("🚀 Booting Inawo System...")
    # Critical: Initialize the bot within the FastAPI event loop
    await bot_app.initialize()
    await bot_app.updater.start_polling()
    await bot_app.start()
    print("✅ System Online: API and Bot are running.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
