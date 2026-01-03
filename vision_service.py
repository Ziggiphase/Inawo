import base64
from io import BytesIO
from PIL import Image

def encode_image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

async def extract_receipt_data(image_bytes):
    base64_image = encode_image_to_base64(image_bytes)
    
    # Prompting Llama 3.2-Vision for specific Nigerian bank details
    prompt = """
    Analyze this bank transfer receipt. Extract the following in JSON format:
    - sender_name: The name of the person who sent the money.
    - amount: The numeric value only (e.g., 5000).
    - date: The transaction date.
    - bank: The name of the bank (e.g., GTBank, Kuda, Zenith).
    - status: 'Success' or 'Pending'.
    Return ONLY the JSON object.
    """

    # Replace with your actual LLM calling logic
    response = await llm_vision_client.chat.completions.create(
        model="llama-3.2-11b-vision-preview", # or your specific model ID
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
