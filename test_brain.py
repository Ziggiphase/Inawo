import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# 1. Load the secret key from your .env file
load_dotenv()

# 2. Initialize the Llama Brain
# Note: llama-3.1-70b-versatile is one of the standard models we used in the academy
llm = ChatGroq(
    model="meta-llama/llama-4-maverick-17b-128e-instruct",
    temperature=0.7
)

# 3. Ask a test question
response = llm.invoke("Hello Llama! Can you help me build Inawo for Nigerian businesses?")

# 4. Print the answer
print("--- BRAIN TEST RESULT ---")
print(response.content)