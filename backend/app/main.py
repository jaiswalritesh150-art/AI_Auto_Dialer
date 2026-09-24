from fastapi import FastAPI, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session

# =====================================================
# DATABASE
# =====================================================

from app.database import Base, engine, get_db

# =====================================================
# MODELS
# =====================================================

from app.models import (
    Lead,
    CallQueue,
    CallAttempt,
    CallIntelligence
)

# =====================================================
# SCHEMAS
# =====================================================

from app.schemas.lead import LeadCreate
from app.schemas.call import CallResultRequest
from app.schemas.intelligence import (
    CallIntelligenceRequest,
    AIConversationRequest
)

# =====================================================
# AI
# =====================================================

from app.ai.analyzer import analyze_call_transcript
from app.telephony.ai_agent import generate_response

# =====================================================
# VALIDATION / SCORING
# =====================================================

from app.validation.service import validate_phone
from app.dialer.scoring import calculate_lead_score

# =====================================================
# DIALER
# =====================================================

from app.dialer.service import (
    queue_lead,
    process_next_call,
    process_specific_call,
    handle_call_result
)

# =====================================================
# TELEPHONY
# =====================================================

from app.telephony.service import (
    initiate_call,
    get_call_status,
    end_call
)

# =====================================================
# CRM
# =====================================================

from app.crm.service import update_lead_after_call


# =====================================================
# DATABASE TABLE CREATION
# =====================================================

Base.metadata.create_all(bind=engine)


# =====================================================
# FASTAPI APP
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
# HEALTH
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

    if queue_item.status != "calling":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Call is not ready for telephony. "
                f"Current status: {queue_item.status}"
            )
        )

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(CallAttempt.attempt_number.desc())
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=400,
            detail="No call attempt found for this queue"
        )

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


# =====================================================
# CALL INTELLIGENCE
# =====================================================

@app.post("/api/v1/call-intelligence")
def create_call_intelligence(
    request: CallIntelligenceRequest,
    db: Session = Depends(get_db)
):

    # =================================================
    # FIND QUEUE
    # =================================================

    queue_item = (
        db.query(CallQueue)
        .filter(
            CallQueue.id == request.queue_id
        )
        .first()
    )

    if not queue_item:
        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # =================================================
    # FIND ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.id == request.attempt_id,
            CallAttempt.queue_id == request.queue_id
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Call attempt not found"
        )

    # =================================================
    # AI ANALYSIS
    # =================================================

    try:

        analysis = analyze_call_transcript(
            request.transcript
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(exc)}"
        )

    # =================================================
    # SAVE INTELLIGENCE
    # =================================================

    intelligence = CallIntelligence(
        queue_id=request.queue_id,
        attempt_id=request.attempt_id,
        transcript=request.transcript,
        summary=analysis["summary"],
        sentiment=analysis["sentiment"],
        outcome=analysis["outcome"]
    )

    db.add(intelligence)
    db.commit()
    db.refresh(intelligence)

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",
        "message": "Call intelligence analyzed and saved successfully",
        "call_intelligence": {
            "id": intelligence.id,
            "queue_id": intelligence.queue_id,
            "attempt_id": intelligence.attempt_id,
            "transcript": intelligence.transcript,
            "summary": intelligence.summary,
            "sentiment": intelligence.sentiment,
            "outcome": intelligence.outcome,
            "analyzed_at": intelligence.analyzed_at
        }
    }


# =====================================================
# AI CALLING
# =====================================================

@app.post("/api/v1/telephony/ai-call/{queue_id}")
def ai_call(
    queue_id: int,
    db: Session = Depends(get_db)
):

    # =================================================
    # FIND QUEUE
    # =================================================

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

    # =================================================
    # FIND LEAD
    # =================================================

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == queue_item.lead_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    # =================================================
    # FIND LATEST ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(CallAttempt.attempt_number.desc())
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=400,
            detail="No call attempt found"
        )

    # =================================================
    # INITIATE SIMULATED CALL
    # =================================================

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

    # =================================================
    # LEAD CONTEXT
    # =================================================

    lead_context = {
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "company": lead.company,
        "lead_source": lead.lead_source,
        "lead_status": lead.lead_status
    }

    # =================================================
    # AI GREETING
    # =================================================

    conversation = [
        {
            "role": "user",
            "text": (
                "Start a natural phone conversation with the lead. "
                "Give a short professional greeting. "
                "Use the lead's name naturally. "
                "Do not mention the phone number."
            )
        }
    ]

    try:

        ai_response = generate_response(
            conversation=conversation,
            lead_context=lead_context
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"AI calling failed: {str(exc)}"
        )

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",
        "message": "AI call initiated successfully",
        "call": {
            "call_id": call["call_id"],
            "queue_id": queue_item.id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "phone": queue_item.phone,
            "lead_name": f"{lead.first_name} {lead.last_name}",
            "status": "ai_calling",
            "ai_response": ai_response
        }
    }


# =====================================================
# AI CALL MESSAGE
# =====================================================

@app.post("/api/v1/telephony/ai-call/{queue_id}/message")
def ai_call_message(
    queue_id: int,
    request: AIConversationRequest,
    db: Session = Depends(get_db)
):

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

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == queue_item.lead_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(CallAttempt.attempt_number.desc())
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=400,
            detail="No call attempt found"
        )

    conversation = list(request.conversation)

    conversation.append({
        "role": "user",
        "text": request.message
    })

    lead_context = {
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "company": lead.company,
        "lead_source": lead.lead_source,
        "lead_status": lead.lead_status
    }

    # =================================================
    # GENERATE AI RESPONSE
    # =================================================

    try:

        ai_response = generate_response(
            conversation=conversation,
            lead_context=lead_context
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"AI response failed: {str(exc)}"
        )

    # =================================================
    # ADD AI RESPONSE
    # =================================================

    conversation.append({
        "role": "model",
        "text": ai_response
    })

    # =================================================
    # BUILD TRANSCRIPT
    # =================================================

    transcript_lines = []

    for message in conversation:

        role = message.get("role", "user")

        if role == "user":
            speaker = "Lead"
        else:
            speaker = "AI Agent"

        transcript_lines.append(
            f"{speaker}: {message.get('text', '')}"
        )

    transcript = "\n".join(transcript_lines)

    # =================================================
    # ANALYZE CONVERSATION
    # =================================================

    try:

        analysis = analyze_call_transcript(
            transcript
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Call intelligence analysis failed: {str(exc)}"
        )

    # =================================================
    # SAVE CALL INTELLIGENCE
    # =================================================

    intelligence = CallIntelligence(
        queue_id=queue_id,
        attempt_id=attempt.id,
        transcript=transcript,
        summary=analysis.get("summary"),
        sentiment=analysis.get("sentiment"),
        outcome=analysis.get("outcome")
    )

    db.add(intelligence)
    db.commit()
    db.refresh(intelligence)

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",
        "message": "AI response and call intelligence saved successfully",
        "call": {
            "queue_id": queue_id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "phone": queue_item.phone,
            "lead_name": f"{lead.first_name} {lead.last_name}",
            "user_message": request.message,
            "ai_response": ai_response,
            "conversation": conversation
        },
        "intelligence": {
            "id": intelligence.id,
            "transcript": intelligence.transcript,
            "summary": intelligence.summary,
            "sentiment": intelligence.sentiment,
            "outcome": intelligence.outcome,
            "analyzed_at": intelligence.analyzed_at
        }
    }


# =====================================================
# END AI CALL + CRM UPDATE
# =====================================================

@app.post("/api/v1/telephony/ai-call/{queue_id}/end")
def end_ai_call(
    queue_id: int,
    db: Session = Depends(get_db)
):

    # =================================================
    # FIND QUEUE
    # =================================================

    queue_item = (
        db.query(CallQueue)
        .filter(
            CallQueue.id == queue_id
        )
        .first()
    )

    if not queue_item:
        raise HTTPException(
            status_code=404,
            detail="Call queue item not found"
        )

    # =================================================
    # FIND LEAD
    # =================================================

    lead = (
        db.query(Lead)
        .filter(
            Lead.id == queue_item.lead_id
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found"
        )

    # =================================================
    # FIND LATEST ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.queue_id == queue_id
        )
        .order_by(CallAttempt.attempt_number.desc())
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=400,
            detail="No call attempt found"
        )

    # =================================================
    # FIND LATEST INTELLIGENCE
    # =================================================

    intelligence = (
        db.query(CallIntelligence)
        .filter(
            CallIntelligence.queue_id == queue_id
        )
        .order_by(CallIntelligence.id.desc())
        .first()
    )

    if not intelligence:
        raise HTTPException(
            status_code=400,
            detail="No call intelligence found"
        )

    # =================================================
    # COMPLETE CALL
    # =================================================

    now = datetime.utcnow()

    attempt.status = "completed"
    attempt.result = intelligence.outcome or "answered"
    attempt.ended_at = now
    attempt.failure_reason = None

    queue_item.status = "completed"
    queue_item.completed_at = now
    queue_item.failure_reason = None

    # =================================================
    # UPDATE CRM
    # =================================================

    crm_result = update_lead_after_call(
        zoho_lead_id=lead.zoho_lead_id,
        outcome=intelligence.outcome or "answered",
        sentiment=intelligence.sentiment or "neutral",
        summary=intelligence.summary or ""
    )

    # =================================================
    # SAVE DATABASE CHANGES
    # =================================================

    db.commit()

    db.refresh(attempt)
    db.refresh(queue_item)

    # =================================================
    # RESPONSE
    # =================================================

    return {
        "status": "success",
        "message": "AI call ended and CRM updated successfully",

        "call": {
            "queue_id": queue_item.id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "call_result": attempt.result,
            "queue_status": queue_item.status,
            "ended_at": attempt.ended_at,
            "completed_at": queue_item.completed_at
        },

        "intelligence": {
            "summary": intelligence.summary,
            "sentiment": intelligence.sentiment,
            "outcome": intelligence.outcome
        },

        "crm": crm_result
    }
