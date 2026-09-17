from fastapi import FastAPI, Depends
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Lead
from app.schemas.lead import LeadCreate
from app.dialer.service import queue_lead


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Auto Dialer API",
    description="Zoho CRM Webhook Backend",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "status": "success",
        "message": "AI Auto Dialer Backend is running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/api/v1/webhooks/zoho/lead")
async def zoho_lead_webhook(
    lead: LeadCreate,
    db: Session = Depends(get_db)
):

    print("\n" + "=" * 60)
    print("ZOHO CRM WEBHOOK RECEIVED")
    print("=" * 60)

    print("\n--- VALIDATED LEAD DATA ---")
    print(lead.model_dump())

    zoho_lead_id = lead.lead_id


    existing_lead = db.query(Lead).filter(
        Lead.zoho_lead_id == zoho_lead_id
    ).first()

    if existing_lead:

        print("\nLead already exists in PostgreSQL.")

        return {
            "status": "success",
            "message": "Lead already exists",
            "lead_id": zoho_lead_id
        }

    new_lead = Lead(
        zoho_lead_id=lead.lead_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        phone=lead.phone,
        email=lead.email,
        lead_source=lead.lead_source,
        lead_status=lead.lead_status
    )

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)


    print("\n--- POSTGRESQL ---")
    print("Lead saved successfully!")
    print(f"Database ID: {new_lead.id}")
    print(f"Zoho Lead ID: {new_lead.zoho_lead_id}")

    dialer_data = queue_lead(new_lead, db)

    print("\n--- DIALER QUEUE ---")
    print("Lead added to dialer queue!")
    print(dialer_data)

    print("\n--- WEBHOOK PROCESSING COMPLETE ---")
    print("=" * 60 + "\n")


    return {
        "status": "success",
        "message": "Lead received, saved and queued for dialing",
        "database_id": new_lead.id,
        "zoho_lead_id": new_lead.zoho_lead_id,
        "dialer": dialer_data,
        "received_at": datetime.now().isoformat()
    }