from fastapi import FastAPI, Request, Depends
from datetime import datetime
from sqlalchemy.orm import Session
import json

from app.database import Base, engine, get_db
from app.models import Lead


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
    request: Request,
    db: Session = Depends(get_db)
):

    print("\n" + "=" * 60)
    print("ZOHO CRM WEBHOOK RECEIVED")
    print("=" * 60)

    # Request headers
    print("\n--- REQUEST HEADERS ---")
    for key, value in request.headers.items():
        print(f"{key}: {value}")

    # Read JSON body
    try:
        body = await request.json()

        print("\n--- LEAD DATA ---")
        print(json.dumps(body, indent=2))

    except Exception as e:
        print("\nERROR READING JSON:")
        print(str(e))

        return {
            "status": "error",
            "message": "Invalid JSON received"
        }

    # Extract lead data
    zoho_lead_id = body.get("lead_id")

    # Check if lead already exists
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

    # Create new lead
    new_lead = Lead(
        zoho_lead_id=zoho_lead_id,
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
        company=body.get("company"),
        phone=body.get("phone"),
        email=body.get("email"),
        lead_source=body.get("lead_source"),
        lead_status=body.get("lead_status")
    )

    # Save to PostgreSQL
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    print("\n--- POSTGRESQL ---")
    print("Lead saved successfully!")
    print(f"Database ID: {new_lead.id}")
    print(f"Zoho Lead ID: {new_lead.zoho_lead_id}")

    print("\n--- WEBHOOK PROCESSING COMPLETE ---")
    print("=" * 60 + "\n")

    return {
        "status": "success",
        "message": "Lead received and saved to PostgreSQL",
        "database_id": new_lead.id,
        "zoho_lead_id": new_lead.zoho_lead_id,
        "received_at": datetime.now().isoformat()
    }