from fastapi import FastAPI, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Lead, CallQueue, CallAttempt

from app.schemas.lead import LeadCreate
from app.schemas.call import CallResultRequest

from app.telephony.service import (
    initiate_call,
    get_call_status,
    end_call
)

from app.dialer.service import (
    queue_lead,
    process_next_call,
    process_specific_call,
    handle_call_result
)

from app.dialer.scoring import calculate_lead_score
from app.validation.service import validate_phone


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

Base.metadata.create_all(bind=engine)


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="AI Auto Dialer API",
    description="Zoho CRM Webhook Backend",
    version="1.0.0"
)


# =====================================================
# ROOT
# =====================================================

@app.get("/")
def root():
    return {
        "status": "success",
        "message": "AI Auto Dialer Backend is running"
    }


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =====================================================
# GET ALL LEADS
# =====================================================

@app.get("/api/v1/leads")
def get_leads(
    db: Session = Depends(get_db)
):

    leads = (
        db.query(Lead)
        .order_by(Lead.id.desc())
        .all()
    )

    return {
        "status": "success",
        "count": len(leads),
        "leads": [
            {
                "id": lead.id,
                "zoho_lead_id": lead.zoho_lead_id,
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "company": lead.company,
                "phone": lead.phone,
                "email": lead.email,
                "lead_source": lead.lead_source,
                "lead_status": lead.lead_status,

                # Lead scoring
                "lead_score": lead.lead_score,
                "priority": lead.priority,

                "created_at": lead.created_at,
                "updated_at": lead.updated_at
            }
            for lead in leads
        ]
    }


# =====================================================
# GET CALL QUEUE
# =====================================================

@app.get("/api/v1/call-queue")
def get_call_queue(
    db: Session = Depends(get_db)
):

    queue_items = (
        db.query(CallQueue)
        .order_by(CallQueue.id.desc())
        .all()
    )

    return {
        "status": "success",
        "count": len(queue_items),
        "call_queue": [
            {
                "id": item.id,
                "lead_id": item.lead_id,
                "phone": item.phone,
                "status": item.status,
                "queued_at": item.queued_at,
                "started_at": item.started_at,
                "completed_at": item.completed_at,
                "failure_reason": item.failure_reason
            }
            for item in queue_items
        ]
    }

# =====================================================
# GET ALL CALL ATTEMPTS
# =====================================================

@app.get("/api/v1/call-attempts")
def get_call_attempts(
    db: Session = Depends(get_db)
):

    attempts = (
        db.query(CallAttempt)
        .order_by(CallAttempt.id.desc())
        .all()
    )

    return {
        "status": "success",
        "count": len(attempts),
        "call_attempts": [
            {
                "id": attempt.id,
                "queue_id": attempt.queue_id,
                "attempt_number": attempt.attempt_number,
                "status": attempt.status,
                "started_at": attempt.started_at,
                "ended_at": attempt.ended_at,
                "result": attempt.result,
                "failure_reason": attempt.failure_reason
            }
            for attempt in attempts
        ]
    }


# =====================================================
# GET CALL ATTEMPTS FOR SPECIFIC QUEUE
# =====================================================

@app.get("/api/v1/call-attempts/{queue_id}")
def get_queue_call_attempts(
    queue_id: int,
    db: Session = Depends(get_db)
):

    # Find queue
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .first()
    )

    if not queue_item:
        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # Find attempts for this queue
    attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_id)
        .order_by(CallAttempt.attempt_number.asc())
        .all()
    )

    return {
        "status": "success",
        "queue_id": queue_id,
        "phone": queue_item.phone,
        "queue_status": queue_item.status,
        "attempt_count": len(attempts),
        "attempts": [
            {
                "id": attempt.id,
                "attempt_number": attempt.attempt_number,
                "status": attempt.status,
                "started_at": attempt.started_at,
                "ended_at": attempt.ended_at,
                "result": attempt.result,
                "failure_reason": attempt.failure_reason
            }
            for attempt in attempts
        ]
    }

# =====================================================
# PROCESS NEXT CALL
# =====================================================

@app.post("/api/v1/dialer/process-next")
def process_next_dialer_call(
    db: Session = Depends(get_db)
):

    result = process_next_call(db)

    if not result:
        return {
            "status": "success",
            "message": "No queued calls available"
        }

    return {
        "status": "success",
        "message": "Next call picked and call attempt started",
        "call": result
    }


# =====================================================
# PROCESS SPECIFIC CALL
# =====================================================

@app.post("/api/v1/dialer/process/{queue_id}")
def process_specific_dialer_call(
    queue_id: int,
    db: Session = Depends(get_db)
):

    result = process_specific_call(
        queue_id=queue_id,
        db=db
    )

    if result.get("success") is False:
        raise HTTPException(
            status_code=404,
            detail=result["message"]
        )

    return {
        "status": "success",
        "message": "Specific call picked and call attempt started",
        "call": result
    }


# =====================================================
# ZOHO CRM WEBHOOK
# =====================================================

@app.post("/api/v1/webhooks/zoho/lead")
async def zoho_lead_webhook(
    lead: LeadCreate,
    db: Session = Depends(get_db)
):

    print("\n" + "=" * 60)
    print("ZOHO CRM WEBHOOK RECEIVED")
    print("=" * 60)

    print("\n--- RECEIVED LEAD DATA ---")
    print(lead.model_dump())

    zoho_lead_id = lead.lead_id


    # =================================================
    # STEP 1 — PHONE VALIDATION
    # =================================================

    phone_validation = validate_phone(lead.phone)

    if not phone_validation["valid"]:

        print("\n--- PHONE VALIDATION FAILED ---")
        print(phone_validation["message"])

        raise HTTPException(
            status_code=400,
            detail={
                "status": "failed",
                "message": "Lead validation failed",
                "reason": phone_validation["message"]
            }
        )

    # Use normalized phone number
    lead.phone = phone_validation["phone"]

    print("\n--- PHONE VALIDATION ---")
    print("Phone:", lead.phone)
    print("Validation:", phone_validation["message"])


    # =================================================
    # STEP 2 — DUPLICATE CHECK
    # =================================================

    existing_lead = (
        db.query(Lead)
        .filter(
            Lead.zoho_lead_id == zoho_lead_id
        )
        .first()
    )

    if existing_lead:

        print("\nLead already exists in PostgreSQL.")

        return {
            "status": "success",
            "message": "Lead already exists",
            "lead_id": zoho_lead_id
        }


    # =================================================
    # STEP 3 — LEAD SCORING
    # =================================================

    lead_score, priority = calculate_lead_score(lead)

    print("\n--- LEAD SCORING ---")
    print("Lead Score:", lead_score)
    print("Priority:", priority)


    # =================================================
    # STEP 4 — CREATE LEAD
    # =================================================

    new_lead = Lead(
        zoho_lead_id=lead.lead_id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        phone=lead.phone,
        email=lead.email,
        lead_source=lead.lead_source,
        lead_status=lead.lead_status,

        # Scoring information
        lead_score=lead_score,
        priority=priority
    )


    # =================================================
    # STEP 5 — SAVE TO POSTGRESQL
    # =================================================

    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)

    print("\n--- POSTGRESQL ---")
    print("Lead saved successfully!")
    print(f"Database ID: {new_lead.id}")
    print(f"Zoho Lead ID: {new_lead.zoho_lead_id}")
    print(f"Lead Score: {new_lead.lead_score}")
    print(f"Priority: {new_lead.priority}")


    # =================================================
    # STEP 6 — ADD TO DIALER QUEUE
    # =================================================

    dialer_data = queue_lead(
        new_lead,
        db
    )

    print("\n--- DIALER QUEUE ---")
    print("Lead added to dialer queue!")
    print(dialer_data)


    # =================================================
    # COMPLETE
    # =================================================

    print("\n--- WEBHOOK PROCESSING COMPLETE ---")
    print("=" * 60 + "\n")


    return {
        "status": "success",
        "message": "Lead received, validated, scored, saved and queued for dialing",

        "database_id": new_lead.id,

        "zoho_lead_id": new_lead.zoho_lead_id,

        "lead_score": new_lead.lead_score,

        "priority": new_lead.priority,

        "dialer": dialer_data,

        "received_at": datetime.now().isoformat()
    }


# =====================================================
# CALL RESULT
# =====================================================

@app.post("/api/v1/dialer/call-result")
def call_result(
    request: CallResultRequest,
    db: Session = Depends(get_db)
):

    result = handle_call_result(
        queue_id=request.queue_id,
        attempt_id=request.attempt_id,
        status=request.status,
        result=request.result,
        failure_reason=request.failure_reason,
        db=db
    )

    if "success" in result and result["success"] is False:
        raise HTTPException(
            status_code=404,
            detail=result["message"]
        )

    return {
        "status": "success",
        "message": "Call result processed successfully",
        "call": result
    }
    
# =====================================================
# INITIATE TELEPHONY CALL
# =====================================================

@app.post("/api/v1/telephony/call/{queue_id}")
def initiate_telephony_call(
    queue_id: int,
    db: Session = Depends(get_db)
):

    # Find queue item
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .first()
    )

    if not queue_item:
        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # Call must already be picked by dialer
    if queue_item.status != "calling":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Call is not ready for telephony. "
                f"Current status: {queue_item.status}"
            )
        )

    # Find the latest call attempt
    attempt = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_id)
        .order_by(CallAttempt.attempt_number.desc())
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=400,
            detail="No call attempt found for this queue"
        )

    # Initiate telephony call
    call = initiate_call(
        phone=queue_item.phone,
        queue_id=queue_item.id,
        attempt_id=attempt.id
    )

    if not call.get("success"):
        raise HTTPException(
            status_code=400,
            detail=call.get("message")
        )

    return {
        "status": "success",
        "message": "Telephony call initiated",
        "call": call
    }

# =====================================================
# GET TELEPHONY CALL STATUS
# =====================================================

@app.get("/api/v1/telephony/call/{call_id}")
def telephony_call_status(
    call_id: str
):

    return get_call_status(call_id)


# =====================================================
# END TELEPHONY CALL
# =====================================================

@app.post("/api/v1/telephony/call/{call_id}/end")
def telephony_end_call(
    call_id: str
):

    return end_call(call_id)