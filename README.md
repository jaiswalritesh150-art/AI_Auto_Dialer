# AI Auto Dialer

AI-powered outbound calling platform for CRM-driven lead management, automated call queues, telephony, AI conversation intelligence, callbacks, retries, and sales analytics.

## Architecture

Zoho CRM ? Lead Webhook ? Validation & Scoring ? Call Queue ? Dialer ? Telephony ? AI Conversation ? Call Intelligence ? Outcome/Callback ? CRM Update ? Dashboard

## Key Features

- Zoho CRM lead webhook integration
- Lead validation and priority scoring
- Automated call queue management
- Call attempt tracking and retry handling
- Callback scheduling and automatic callback processing
- Exotel telephony integration
- Mock telephony provider for development/testing
- Gemini-powered AI conversation
- Transcript analysis and summarization
- Sentiment and call outcome detection
- Callback intent detection
- Post-call CRM updates
- Call history and duration tracking
- Stale call recovery
- Sales analytics dashboard

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- Google Gemini API
- Zoho CRM API
- Exotel API

### Frontend
- React
- Vite
- JavaScript
- CSS

### Infrastructure
- Docker
- Git / GitHub

## Project Structure

```text
AI_Auto_Dialer/
+-- backend/
¦   +-- app/
¦   ¦   +-- crm/
¦   ¦   +-- dialer/
¦   ¦   +-- telephony/
¦   ¦   +-- models.py
¦   ¦   +-- main.py
¦   +-- requirements.txt
+-- frontend/
¦   +-- src/
¦   ¦   +-- App.jsx
¦   +-- package.json
+-- .env.example
+-- .gitignore
+-- README.md
