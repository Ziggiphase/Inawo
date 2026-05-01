# Inawo AI: The Instant Onboarding Agent for MSMEs 🇳🇬

Inawo AI is a specialized AI agent designed to help Nigerian vendors (Caterers, Fashion Designers, Event Planners) automate their customer interactions. 

### 🚀 The Problem
Small businesses in Nigeria lose sales when they are too busy to respond to price inquiries on Telegram/WhatsApp. Manually setting up a chatbot is too technical and time-consuming for them.

### 💡 Our Solution: "Document-to-Agent"
Inawo allows a vendor to upload their **existing** Excel, PDF, or Word price list. Our system parses these documents and "trains" a LangGraph-powered AI agent in seconds.

## 🛠 Technical Architecture
- **Frontend:** React-based portal (via Lovable) for vendor onboarding.
- **Backend:** FastAPI (Python) handling multipart form-data and file extraction.
- **AI Brain:** LangGraph + LangChain + Groq (Llama 3.3 70B).
- **File Processing:** - `pdfplumber` for high-fidelity PDF text extraction.
  - `pandas` for Excel/CSV data structure flattening.
  - `python-docx` for Word document parsing.
- **Deployment:** Render (Unified Web + Worker process).

## 📂 Project Structure
- `main.py`: Entry point. Manages the FastAPI server and the Telegram Bot background task.
- `inawo_bot.py`: Telegram interface using `python-telegram-bot`.
- `inawo_logic.py`: The LangGraph state machine that manages conversation memory.
- `registry.json`: The "Active Memory" where vendor data is stored.
