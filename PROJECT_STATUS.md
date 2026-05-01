# Inawo Project Status & Roadmap

This document outlines the architectural milestones achieved during the transformation of Inawo from a hackathon prototype into a production-ready B2B2C SaaS platform, as well as the remaining features needed for full launch.

## ✅ Phase 1: What Has Been Completed

### 1. Architectural Overhaul
- Decoupled the monolithic Python script into a robust **FastAPI + Next.js** architecture.
- Replaced local file storage with a fully relational **PostgreSQL** database schema.

### 2. Database Schema (B2B2C Model)
- `Business`: Stores vendor details, brand colors, knowledge base, and AI active status.
- `Customer` & `ChatSession`: Tracks user interactions across WhatsApp and Telegram.
- `ChatMessage`: Logs the entire conversation history, identifying sender roles (`user` vs `ai`).
- `Order`: Tracks shopping carts and verified purchases.

### 3. Frontend Web Application (Next.js)
- **Design System**: Implemented a premium, dark-themed, glassmorphism UI.
- **B2C Marketplace (`/explore`)**: A dynamic directory fetching active businesses from the database.
- **B2C Storefront (`/b/[id]`)**: Auto-generated business profile pages displaying custom brand colors and product catalogs.
- **Authentication**: JWT-based login and signup flow.
- **B2B Dashboard**:
  - `Overview`: Analytics dashboard displaying Conversion Rates and AI Autopilot status.
  - `Operations`: Live data table showing recent orders and active WhatsApp sessions.
  - `Catalog Upload`: Drag-and-drop interface for document ingestion.
  - `Settings`: UI to configure the AI's system prompt (knowledge base) and brand theme.

### 4. Backend Engine & Integrations
- **WhatsApp Webhook**: Verified and handles incoming text and image messages.
- **Human-in-the-Loop**: "Kill Switch" implemented. If `is_ai_active` is false, the LangGraph agent pauses, allowing human takeover.
- **Vision AI**: Integrated Groq Vision (Llama 3.2 11B) to analyze payment receipts and update order statuses.
- **Telegram Bot**: Fully refactored `inawo_bot.py` to use the new `Business` and `Order` models.

---

## 🚧 Phase 2: What is Yet To Be Done (Next Steps)

### 1. Core Platform Logic
- **Document Parsing Implementation**: The `/api/catalog/upload` endpoint currently accepts files, but the actual PDF/Excel extraction logic needs to be finalized to insert extracted items directly into the PostgreSQL `Product` table.
- **LangChain Tool Integration**: Connect the LangGraph AI to dynamically search the `Product` table (using vector embeddings or SQL queries) when a customer asks about inventory.

### 2. Dashboard Enhancements
- **Live Chat Interface**: Build a messaging UI in the dashboard so business owners can actually read and reply to WhatsApp messages when they trigger the AI Kill Switch.
- **Websockets**: Implement WebSocket connections in FastAPI so the dashboard updates with new orders and messages instantly without refreshing.

### 3. Security & Production Readiness
- **Alembic Migrations**: Setup Alembic to handle future database schema changes safely without dropping tables.
- **Webhook Security**: Implement HMAC SHA256 signature verification for the WhatsApp webhook to ensure incoming requests are genuinely from Meta.
- **Password Reset Flow**: Add email verification and password reset functionality.

### 4. Deployment
- **Frontend**: Deploy the Next.js application to **Vercel**.
- **Backend & Database**: Deploy the FastAPI server and PostgreSQL database to **Render**, **Railway**, or **AWS**.
- **Permanent Webhooks**: Update the Meta Developer portal with the production Render URL instead of the local Ngrok link.
