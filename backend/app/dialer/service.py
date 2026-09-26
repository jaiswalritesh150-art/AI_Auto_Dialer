from datetime import datetime

from sqlalchemy.orm import Session

from app.models import CallQueue, CallAttempt
from app.telephony.service import initiate_call


# =====================================================
# QUEUE LEAD
# =====================================================

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


# =====================================================
# PROCESS NEXT CALL
# =====================================================

def process_next_call(db: Session):
    """
    Pick the oldest queued call and create the next call attempt.

    Maximum attempts = 3.
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

    # Count previous attempts
    previous_attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_item.id)
        .count()
    )

    # Calculate next attempt number
    attempt_number = previous_attempts + 1

    # Safety check
    if attempt_number > 3:
        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = "Maximum call attempts reached"

        db.commit()

        return {
            "queue_id": queue_item.id,
            "phone": queue_item.phone,
            "queue_status": queue_item.status,
            "message": "Maximum call attempts reached"
        }

    # Mark queue item as calling
    queue_item.status = "calling"

    # Set initial start time only once
    if queue_item.started_at is None:
        queue_item.started_at = datetime.utcnow()

    # Create new call attempt
    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=attempt_number,
        status="started",
        started_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Initiate telephony call
    call = initiate_call(
        phone=queue_item.phone,
        queue_id=queue_item.id,
        attempt_id=attempt.id
    )

    if not call.get("success"):
        attempt.status = "failed"
        attempt.failure_reason = call.get("message")
        attempt.ended_at = datetime.utcnow()

        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = call.get("message")

        db.commit()

        return {
            "queue_id": queue_item.id,
            "phone": queue_item.phone,
            "queue_status": queue_item.status,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "failure_reason": attempt.failure_reason
        }

    # Save provider tracking information
    attempt.provider = call.get("provider")
    attempt.provider_call_id = call.get("call_id")
    attempt.status = "initiated"

    db.commit()
    db.refresh(attempt)

    return {
        "queue_id": queue_item.id,
        "phone": queue_item.phone,
        "queue_status": queue_item.status,
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "attempt_status": attempt.status,
        "provider": attempt.provider,
        "provider_call_id": attempt.provider_call_id,
        "started_at": attempt.started_at,
    }


# =====================================================
# PROCESS SPECIFIC CALL
# =====================================================

def process_specific_call(
    queue_id: int,
    db: Session
):
    """
    Process a specific call queue item using queue_id.

    Creates the next call attempt for that queue.

    Maximum attempts = 3.
    """

    # Find specific queue item
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .first()
    )

    if not queue_item:
        return {
            "success": False,
            "message": "Call queue item not found"
        }

    # Only queued calls can be processed
    if queue_item.status != "queued":
        return {
            "success": False,
            "message": (
                f"Call is not queued. "
                f"Current status: {queue_item.status}"
            )
        }

    # Count previous attempts
    previous_attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_id)
        .count()
    )

    # Calculate next attempt number
    attempt_number = previous_attempts + 1

    # Maximum 3 attempts
    if attempt_number > 3:
        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = "Maximum call attempts reached"

        db.commit()

        return {
            "success": False,
            "message": "Maximum call attempts reached",
            "queue_id": queue_id
        }

    # Mark queue as calling
    queue_item.status = "calling"

    # Keep original started_at
    if queue_item.started_at is None:
        queue_item.started_at = datetime.utcnow()

    # Create new call attempt
    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=attempt_number,
        status="started",
        started_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Initiate telephony call
    call = initiate_call(
        phone=queue_item.phone,
        queue_id=queue_item.id,
        attempt_id=attempt.id
    )

    if not call.get("success"):
        attempt.status = "failed"
        attempt.failure_reason = call.get("message")
        attempt.ended_at = datetime.utcnow()

        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = call.get("message")

        db.commit()

        return {
            "success": False,
            "queue_id": queue_item.id,
            "phone": queue_item.phone,
            "queue_status": queue_item.status,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "failure_reason": attempt.failure_reason
        }

    # Save provider tracking information
    attempt.provider = call.get("provider")
    attempt.provider_call_id = call.get("call_id")
    attempt.status = "initiated"

    db.commit()
    db.refresh(attempt)

    return {
        "success": True,
        "queue_id": queue_item.id,
        "phone": queue_item.phone,
        "queue_status": queue_item.status,
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "attempt_status": attempt.status,
        "provider": attempt.provider,
        "provider_call_id": attempt.provider_call_id,
        "started_at": attempt.started_at
    }


# =====================================================
# HANDLE CALL RESULT
# =====================================================

def handle_call_result(
    queue_id: int,
    attempt_id: int,
    status: str,
    result: str | None,
    failure_reason: str | None,
    db: Session
):
    """
    Process the result of a call attempt.

    Successful call:
        completed

    Retryable results:
        no_answer
        busy
        failed

    Maximum attempts:
        3
    """

    # =================================================
    # FIND QUEUE ITEM
    # =================================================

    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .first()
    )

    if not queue_item:
        return {
            "success": False,
            "message": "Call queue item not found"
        }

    # =================================================
    # FIND CALL ATTEMPT
    # =================================================

    attempt = (
        db.query(CallAttempt)
        .filter(CallAttempt.id == attempt_id)
        .first()
    )

    if not attempt:
        return {
            "success": False,
            "message": "Call attempt not found"
        }

    # =================================================
    # VERIFY ATTEMPT BELONGS TO QUEUE
    # =================================================

    if attempt.queue_id != queue_id:
        return {
            "success": False,
            "message": "Call attempt does not belong to this queue"
        }

    # =================================================
    # UPDATE ATTEMPT
    # =================================================

    attempt.status = status
    attempt.result = result
    attempt.failure_reason = failure_reason
    attempt.ended_at = datetime.utcnow()

    # =================================================
    # COMPLETED CALL
    # =================================================

    if status == "completed":

        queue_item.status = "completed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = None

        db.commit()

        db.refresh(attempt)
        db.refresh(queue_item)

        return {
            "queue_id": queue_item.id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "queue_status": queue_item.status,
            "attempt_status": attempt.status,
            "result": attempt.result,
            "failure_reason": attempt.failure_reason,
            "ended_at": attempt.ended_at,
            "completed_at": queue_item.completed_at,
            "retry": False
        }

    # =================================================
    # RETRYABLE RESULTS
    # =================================================

    retryable_results = {
        "no_answer",
        "busy",
        "failed"
    }

    if result in retryable_results:

        # Retry available
        if attempt.attempt_number < 3:

            queue_item.status = "queued"
            queue_item.completed_at = None
            queue_item.failure_reason = failure_reason

            db.commit()

            db.refresh(attempt)
            db.refresh(queue_item)

            return {
                "queue_id": queue_item.id,
                "attempt_id": attempt.id,
                "attempt_number": attempt.attempt_number,
                "queue_status": queue_item.status,
                "attempt_status": attempt.status,
                "result": attempt.result,
                "failure_reason": attempt.failure_reason,
                "ended_at": attempt.ended_at,
                "completed_at": queue_item.completed_at,
                "retry": True,
                "next_attempt": attempt.attempt_number + 1
            }

        # =================================================
        # MAXIMUM ATTEMPTS REACHED
        # =================================================

        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = (
            failure_reason or "Maximum call attempts reached"
        )

        db.commit()

        db.refresh(attempt)
        db.refresh(queue_item)

        return {
            "queue_id": queue_item.id,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "queue_status": queue_item.status,
            "attempt_status": attempt.status,
            "result": attempt.result,
            "failure_reason": queue_item.failure_reason,
            "ended_at": attempt.ended_at,
            "completed_at": queue_item.completed_at,
            "retry": False,
            "message": "Maximum call attempts reached"
        }

    # =================================================
    # OTHER / UNKNOWN STATUS
    # =================================================

    queue_item.status = status
    queue_item.completed_at = datetime.utcnow()
    queue_item.failure_reason = failure_reason

    db.commit()

    db.refresh(attempt)
    db.refresh(queue_item)

    return {
        "queue_id": queue_item.id,
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "queue_status": queue_item.status,
        "attempt_status": attempt.status,
        "result": attempt.result,
        "failure_reason": attempt.failure_reason,
        "ended_at": attempt.ended_at,
        "completed_at": queue_item.completed_at,
        "retry": False
    }


# =====================================================
# SCHEDULE CALLBACK
# =====================================================

def schedule_callback(
    queue_id: int,
    callback_at: datetime,
    db: Session
):
    """
    Schedule a callback for an existing call queue item.
    """

    # Find queue item
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .first()
    )

    if not queue_item:
        return {
            "success": False,
            "message": "Call queue item not found"
        }

    # Save callback details
    queue_item.callback_at = callback_at
    queue_item.callback_status = "scheduled"

    # Update queue status
    queue_item.status = "callback_scheduled"

    queue_item.completed_at = None
    queue_item.failure_reason = None

    db.commit()
    db.refresh(queue_item)

    return {
        "success": True,
        "queue_id": queue_item.id,
        "callback_at": queue_item.callback_at,
        "callback_status": queue_item.callback_status,
        "queue_status": queue_item.status,
        "message": "Callback scheduled successfully"
    }


# =====================================================
# PROCESS DUE CALLBACKS
# =====================================================

def process_due_callbacks(db: Session):
    """
    Find scheduled callbacks whose callback time has arrived.

    Due callbacks are moved into the normal dialing queue
    and immediately processed into a new call attempt.
    """

    now = datetime.utcnow()

    due_callbacks = (
        db.query(CallQueue)
        .filter(
            CallQueue.status == "callback_scheduled",
            CallQueue.callback_at <= now
        )
        .all()
    )

    processed_callbacks = []

    for queue_item in due_callbacks:

        # -------------------------------------------------
        # Move callback back to normal dialing queue
        # -------------------------------------------------

        queue_item.status = "queued"
        queue_item.callback_status = "ready"

        db.commit()

        # -------------------------------------------------
        # Automatically create a new call attempt
        # -------------------------------------------------

        call_result = process_specific_call(
            queue_id=queue_item.id,
            db=db
        )

        processed_callbacks.append({
            "queue_id": queue_item.id,
            "callback_at": queue_item.callback_at,
            "callback_status": queue_item.callback_status,
            "queue_status": call_result.get(
                "queue_status",
                queue_item.status
            ),
            "attempt_id": call_result.get("attempt_id"),
            "attempt_number": call_result.get("attempt_number"),
            "attempt_status": call_result.get("attempt_status"),
            "success": call_result.get("success", False)
        })

    return {
        "success": True,
        "processed_count": len(processed_callbacks),
        "callbacks": processed_callbacks
    }






