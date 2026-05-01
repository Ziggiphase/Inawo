# Inawo AI Platform

Inawo is an enterprise-grade B2B2C marketplace designed to empower Nigerian MSMEs with 24/7 autonomous AI agents. The platform handles customer inquiries, automates order processing, and facilitates transactions via WhatsApp and Telegram, all managed through a premium Next.js web dashboard.

## 🚀 Tech Stack

**Backend (AI Engine & API):**
- Python 3.10+
- FastAPI (REST API & Webhooks)
- PostgreSQL & SQLAlchemy (Database & ORM)
- LangGraph & LangChain (AI Orchestration)
- Groq Cloud (Llama 3.3 70B & Vision models)

**Frontend (Dashboard & Marketplace):**
- Next.js (App Router)
- React & TypeScript
- Custom Glassmorphism Design System (Vanilla CSS)

## 📁 Project Structure

```
Inawo/
├── backend/                  # FastAPI Application
│   ├── main.py               # Application entry point & WhatsApp Webhooks
│   ├── models.py             # PostgreSQL Database Schema
│   ├── database.py           # DB Connection Setup
│   ├── inawo_logic.py        # LangGraph AI Agent Logic
│   ├── inawo_bot.py          # Telegram Bot Integration
│   ├── api_*.py              # API Routers (Analytics, Auth, Catalog, Public)
│   └── requirements.txt      # Python Dependencies
│
└── frontend/                 # Next.js Application
    ├── src/app/              # Next.js App Router Pages
    │   ├── dashboard/        # B2B Control Center & Operations
    │   ├── explore/          # B2C Public Marketplace Directory
    │   ├── b/[id]/           # B2C Dynamic Storefronts
    │   ├── login/            # Authentication
    │   └── signup/           # Business Onboarding
    └── package.json          # Node Dependencies
```

## 🛠️ Local Development Setup

### 1. Database Setup
Ensure PostgreSQL is installed and running on your system.
Create a new database named `inawo_db`.

### 2. Backend Environment Variables
Create a `.env` file in the `backend/` directory:
```ini
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/inawo_db
GROQ_API_KEY=your_groq_api_key
WHATSAPP_VERIFY_TOKEN=your_custom_webhook_verify_string
WHATSAPP_PHONE_NUMBER_ID=your_meta_phone_id
WHATSAPP_API_TOKEN=your_meta_system_user_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
SECRET_KEY=your_jwt_secret_key
```

### 3. Running the Backend
Open a terminal in the `backend` directory:
```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 10000
```
*(On first run, SQLAlchemy will automatically create all tables in your PostgreSQL database).*

### 4. Running the Frontend
Open a separate terminal in the `frontend` directory:
```bash
npm install
npm run dev
```
The web application will be available at `http://localhost:3000`.

### 5. Webhook Configuration (Ngrok)
To allow Meta/WhatsApp to communicate with your local backend:
1. Install Ngrok.
2. Run `ngrok http 10000`.
3. Copy the secure `https://...ngrok-free.app` URL.
4. Go to the Meta Developer Portal > WhatsApp > Configuration.
5. Set the Callback URL to `https://[your-ngrok-url]/webhook`.
6. Enter your `WHATSAPP_VERIFY_TOKEN` and save.
