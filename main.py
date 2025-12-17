from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# IMPORTANT: This allows your Lovable frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/onboard")
async def onboard_vendor(request: Request):
    vendor_data = await request.json()
    
    # Save the vendor's data to a file called 'registry.json'
    # In a real SaaS, this would be a SQL database.
    with open("registry.json", "w") as f:
        json.dump(vendor_data, f)
        
    print(f"New Vendor Registered: {vendor_data['businessName']}")
    return {"status": "success", "message": "Inawo AI is now active!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)