from datetime import datetime

from sqlalchemy.orm import Session

from app.models import CallQueue, CallAttempt


def queue_lead(lead, db: Session):
    """
    Add a lead to the PostgreSQL call queue.
    Actual calling provider will be connected later.
    """

    queue_item = CallQueue(
        lead_id=lead.id,
        phone=lead.phone,
        status="queued",
        queued_at=datetime.utcnow()
    )

    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)

    return {
        "queue_id": queue_item.id,
        "lead_id": lead.zoho_lead_id,
        "name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "phone": lead.phone,
        "status": queue_item.status,
        "queued_at": queue_item.queued_at,
    }


def process_next_call(db: Session):
    """
    Pick the next queued lead and create a call attempt.
    Actual telephony provider will be connected later.
    """

    # Find the oldest queued call
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.status == "queued")
        .order_by(CallQueue.queued_at.asc())
        .first()
    )

    if not queue_item:
        return None

    # Mark queue item as calling
    queue_item.status = "calling"
    queue_item.started_at = datetime.utcnow()

    # Create first call attempt
    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=1,
        status="started",
        started_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "queue_id": queue_item.id,
        "phone": queue_item.phone,
        "queue_status": queue_item.status,
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "attempt_status": attempt.status,
        "started_at": attempt.started_at,
    }