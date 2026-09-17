from datetime import datetime
from sqlalchemy.orm import Session
from app.models import CallQueue


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