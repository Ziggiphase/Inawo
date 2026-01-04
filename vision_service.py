import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import os
import json

# Initialize Groq Vision
llm_vision = ChatGroq(
    model="llama-3.2-11b-vision-preview",
    temperature=0,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

async def extract_receipt_details(image_bytes):
    """Analyzes a bank receipt and returns structured JSON for payment verification."""
    base64_image = encode_image(image_bytes)
    
    prompt = (
        "Analyze this Nigerian bank transfer receipt. "
        "Extract the following and return ONLY a valid JSON object: "
        "{"
        "'sender_name': 'Full name', "
        "'amount': 'Numerical value only', "
        "'bank': 'Bank name', "
        "'ref': 'Transaction reference/ID number', "
        "'status': 'Success/Failed'"
        "}"
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
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Vision Error: {e}")
        return {"error": "Could not parse receipt"}
