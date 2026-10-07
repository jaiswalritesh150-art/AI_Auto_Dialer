# AI Auto Dialer

AI-powered outbound calling platform for CRM-driven lead management, automated call queues, telephony integration, AI conversation intelligence, callbacks, retries, and sales analytics.

## Overview

AI Auto Dialer automates the outbound sales calling workflow from CRM lead ingestion to call processing and post-call analysis.

The system integrates with Zoho CRM for lead management, Exotel for telephony, Google Gemini for AI-powered conversation and call intelligence, and PostgreSQL for persistent data storage.

## Architecture

Zoho CRM
   |
   v
Lead Webhook
   |
   v
Validation & Lead Scoring
   |
   v
Call Queue
   |
   v
Dialer
   |
   v
Telephony (Exotel / Mock)
   |
   v
AI Conversation
   |
   v
Call Intelligence
   |
   +------> Outcome
   |
   +------> Callback Scheduling
   |
   v
Zoho CRM Update
   |
   v
Sales Dashboard

## Key Features

* Zoho CRM lead webhook integration
* Phone number validation and normalization
* Automatic lead scoring and priority assignment
* Automated call queue management
* Call attempt tracking
* Retry handling
* Exotel telephony integration
* Mock telephony provider for development and testing
* Gemini-powered AI conversation
* Conversation transcript generation
* Call summarization
* Sentiment detection
* Call outcome detection
* Callback intent detection
* Callback scheduling
* Automatic callback processing
* Post-call CRM updates
* Call history and duration tracking
* Stale call recovery
* Sales analytics dashboard
* REST API with FastAPI
* PostgreSQL database persistence

## Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pydantic
* Google Gemini API
* Zoho CRM API
* Exotel API

### Frontend

* React
* Vite
* JavaScript
* CSS

### Infrastructure

* Docker
* PostgreSQL
* Render
* Git
* GitHub

## Project Structure

AI_Auto_Dialer/
|
+-- backend/
|   |
|   +-- app/
|   |   +-- crm/
|   |   +-- dialer/
|   |   +-- telephony/
|   |   +-- ai/
|   |   +-- models.py
|   |   +-- main.py
|   |
|   +-- requirements.txt
|   +-- .env.example
|
+-- frontend/
|   |
|   +-- src/
|   |   +-- App.jsx
|   |
|   +-- package.json
|
+-- .env.example
+-- .gitignore
+-- README.md
```

## Local Setup

### 1. Clone the repository


git clone https://github.com/jaiswalritesh150-art/AI_Auto_Dialer.git
cd AI_Auto_Dialer

### 2. Backend setup

cd backend
python -m venv venv

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a reference.

Required integrations may include:

```text
DATABASE_URL
GEMINI_API_KEY
ZOHO_CLIENT_ID
ZOHO_CLIENT_SECRET
ZOHO_REFRESH_TOKEN
EXOTEL_API_KEY
EXOTEL_API_TOKEN
EXOTEL_ACCOUNT_SID
EXOTEL_CALLER_ID
EXOTEL_TEST_TO
```

For local telephony testing without making a real Exotel call:

```text
TELEPHONY_MODE=mock
```

For live Exotel calling:

```text
TELEPHONY_MODE=live
```

Never commit `.env` or API credentials to GitHub.

### 4. Start PostgreSQL

The project can use PostgreSQL through Docker.

Example:

```bash
docker start ai-dialer-postgres
```

If the container does not exist, create/configure PostgreSQL according to the environment variables in `.env`.

### 5. Start the backend

From the `backend` directory:

```bash
python -m uvicorn app.main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend uses:

```text
VITE_API_BASE_URL
```

For local development:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For the deployed backend:

```text
VITE_API_BASE_URL=https://ai-auto-dialer-backend.onrender.com
```

## Main API Areas

| Area                  | Endpoint                                       |
| --------------------- | ---------------------------------------------- |
| Health                | `/health`                                      |
| Leads                 | `/api/v1/leads`                                |
| Zoho Lead Webhook     | `/api/v1/webhooks/zoho/lead`                   |
| Call Queue            | `/api/v1/call-queue`                           |
| Call Attempts         | `/api/v1/call-attempts`                        |
| Dashboard Stats       | `/api/v1/dashboard/stats`                      |
| Process Next Call     | `/api/v1/dialer/process-next`                  |
| Process Specific Call | `/api/v1/dialer/process/{queue_id}`            |
| Call Result           | `/api/v1/dialer/call-result`                   |
| AI Call               | `/api/v1/telephony/ai-call/{queue_id}`         |
| AI Conversation       | `/api/v1/telephony/ai-call/{queue_id}/message` |
| Call Intelligence     | `/api/v1/...`                                  |
| Callback Processing   | `/api/v1/dialer/callback/process-due`          |

The complete interactive API documentation is available through FastAPI Swagger at `/docs`.

## Telephony Modes

### Mock Mode

Mock mode is intended for development and testing when a real telephony provider is unavailable.

```text
TELEPHONY_MODE=mock
```

It simulates call initiation and generates a mock provider call ID without making an external phone call.

This mode was used to validate the complete local call lifecycle:

```text
Lead
  -> Queue
  -> Dialer
  -> Mock Call
  -> Call Attempt
  -> Call Result
  -> Completed Call
  -> Dashboard Analytics
```

### Live Mode

Live mode uses the Exotel API:

```text
TELEPHONY_MODE=live
```

Live calling depends on a properly configured Exotel account, credentials, caller ID, destination number, and provider-side account/KYC approval.

During development, live Exotel calls were blocked by the provider's KYC/account restrictions, so mock mode was used for end-to-end testing.

## Deployment

### Backend

Deployed backend:

```text
https://ai-auto-dialer-backend.onrender.com
```

### Frontend

Deployed frontend:

```text
https://ai-auto-dialer-frontend.onrender.com
```

The frontend is configured to communicate with the deployed FastAPI backend through:

```text
VITE_API_BASE_URL
```

## Testing

The project has been tested for:

* Backend health check
* Lead creation through CRM webhook
* Lead scoring
* Call queue creation
* Call processing
* Mock telephony initiation
* Call attempt tracking
* Call result processing
* Completed call status
* Call duration tracking
* Dashboard statistics
* Production frontend/backend connectivity

Example successful mock call lifecycle:

```text
Lead ID: MOCK-TEST-001
Queue ID: 26
Attempt ID: 41
Provider: mock
Result: answered
Final Queue Status: completed
```

## Security

* API credentials are stored in environment variables.
* `.env` is excluded from Git tracking.
* Secrets should never be committed to the repository.
* Production credentials should be configured through the deployment platform's environment settings.

## Future Improvements

Possible future improvements include:

* Production-grade telephony scaling
* Advanced call scheduling
* More detailed sales analytics
* Role-based authentication and authorization
* Real-time call monitoring
* Enhanced AI conversation memory
* Advanced CRM synchronization
* Background job queue using Redis/Celery
* Horizontal scaling for high call volumes

## Author

**Ritesh Jaiswal**

AI/ML Engineering Student
Generative AI | FastAPI | React | Automation
