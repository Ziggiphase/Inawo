import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import os
import json
import re

# Initialize Groq Vision (using the fast 11B vision model)
llm_vision = ChatGroq(
    model="llama-3.2-11b-vision-preview",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

async def extract_receipt_details(image_bytes):
    """
    Analyzes a bank receipt and returns structured JSON.
    Optimized for Nigerian Bank Apps (GTB, Zenith, Kuda, Moniepoint, etc.)
    """
    base64_image = encode_image(image_bytes)
    
    # Precise prompt to avoid AI 'chatter'
    prompt = (
        "You are a financial auditor. Examine this Nigerian bank transfer receipt image. "
        "Extract the following details and return ONLY a raw JSON object. "
        "Do not include any explanations or markdown backticks. "
        "Required Fields: "
        "{"
        "\"sender_name\": \"string\", "
        "\"amount\": number, "
        "\"bank\": \"string\", "
        "\"ref\": \"string\", "
        "\"status\": \"Success/Failed\""
        "}"
        "Note: For amount, extract ONLY the digits (e.g., 5000 not N5,000)."
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
        ]
    )

    try:
        response = await llm_vision.ainvoke([message])
        content = response.content.strip()
        
        # Clean up any potential markdown garbage (```json ... ```)
        clean_json = re.sub(r'```(?:json)?|```', '', content).strip()
        
        data = json.loads(clean_json)
        
        # Log for Render tracking
        print(f"✅ Receipt Parsed: ₦{data.get('amount')} from {data.get('bank')}")
        return data

    except Exception as e:
        print(f"❌ Vision Parsing Error: {e}")
        return {"error": "Could not parse receipt", "details": str(e)}
