import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import os
import json

# Initialize the Groq Vision model
# llama-3.2-11b-vision-preview is excellent for structured data extraction
llm_vision = ChatGroq(
    model="llama-3.2-11b-vision-preview",
    temperature=0,  # Set to 0 for consistent, factual extraction
    groq_api_key=os.getenv("GROQ_API_KEY")
)

def encode_image(image_bytes):
    """Converts image bytes to a base64 string for the API."""
    return base64.b64encode(image_bytes).decode("utf-8")

async def extract_receipt_details(image_bytes):
    """
    Analyzes a bank receipt image and returns structured JSON.
    """
    base64_image = encode_image(image_bytes)
    
    # Prompt optimized for Nigerian bank transfer screenshots
    prompt = (
        "Analyze this Nigerian bank transfer receipt/screenshot. "
        "Extract the following details and return ONLY a valid JSON object: "
        "{ "
        "'sender_name': 'Full name of sender', "
        "'amount': 'Numerical value only, no commas', "
        "'date': 'Transaction date', "
        "'bank': 'Name of the bank (e.g. OPay, Kuda, GTB)', "
        "'status': 'Success, Pending, or Failed' "
        "}"
    )

    # LangChain Multimodal Message Format
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
        # Clean up the response in case the model adds markdown backticks
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"Vision Error: {e}")
        return {"error": "Could not parse receipt"}
