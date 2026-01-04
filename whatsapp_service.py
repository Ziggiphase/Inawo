import httpx
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERSION = "v21.0" # Meta API version

async def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v21.0/{os.getenv('PHONE_NUMBER_ID')}/messages"
    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        # --- THE DEBUGGER ---
        print(f"📤 Outbound Status: {response.status_code}")
        print(f"📤 Outbound Body: {response.text}")
        return response.json()
async def get_whatsapp_media_bytes(media_id: str):
    """Fetches and downloads media from Meta's servers."""
    url = f"https://graph.facebook.com/{VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient() as client:
        # Step 1: Get the download URL
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        media_url = response.json().get("url")
        
        # Step 2: Download the actual bytes
        media_response = await client.get(media_url, headers=headers)
        if media_response.status_code == 200:
            return media_response.content
    return None

    

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"❌ WhatsApp Error: {response.text}")
        return response.json()
