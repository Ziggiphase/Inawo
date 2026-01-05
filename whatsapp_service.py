import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration - Centralized to avoid retrieval errors
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERSION = "v21.0" 

async def send_whatsapp_message(to_number: str, text: str):
    """Sends a plain text message via the WhatsApp Business API."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("❌ Error: WHATSAPP_TOKEN or PHONE_NUMBER_ID missing from environment.")
        return None

    # Clean the phone number (ensure no '+', just digits)
    clean_number = "".join(filter(str.isdigit, to_number))
    
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_number,
        "type": "text",
        "text": {"body": text},
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            # Log the result for Render debugging
            if response.status_code == 200:
                print(f"✅ WhatsApp sent to {clean_number}")
            else:
                print(f"❌ WhatsApp API Error ({response.status_code}): {response.text}")
            return response.json()
        except Exception as e:
            print(f"⚠️ Connection Error in WhatsApp Service: {e}")
            return None

async def get_whatsapp_media_bytes(media_id: str):
    """Fetches and downloads media (like receipts) from Meta's servers."""
    if not WHATSAPP_TOKEN:
        return None
        
    url = f"https://graph.facebook.com/{VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Get the temporary download URL
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return None
            
            media_url = response.json().get("url")
            
            # Step 2: Download the actual file bytes
            media_response = await client.get(media_url, headers=headers)
            if media_response.status_code == 200:
                return media_response.content
        except Exception as e:
            print(f"⚠️ Media Download Error: {e}")
            
    return None
