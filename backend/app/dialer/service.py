from datetime import datetime

from sqlalchemy.orm import Session

from app.models import CallQueue, CallAttempt, Lead
from app.telephony.service import initiate_call
from app.crm.service import update_lead_after_call


# =====================================================
# QUEUE LEAD
# =====================================================

def queue_lead(lead, db: Session):
    """
    Add a lead to the PostgreSQL call queue.
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

    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.status == "queued")
        .order_by(CallQueue.queued_at.asc())
        .first()
    )

    if not queue_item:
        return None

    previous_attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_item.id)
        .count()
    )

    attempt_number = previous_attempts + 1

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

    queue_item.status = "calling"

    if queue_item.started_at is None:
        queue_item.started_at = datetime.utcnow()

    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=attempt_number,
        status="started",
        started_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    call = initiate_call(
        phone=queue_item.phone,
        queue_id=queue_item.id,
        attempt_id=attempt.id
    )

    # -------------------------------------------------
    # TELEPHONY FAILURE
    # -------------------------------------------------

    if not call.get("success"):

        attempt.status = "failed"
        attempt.failure_reason = call.get("message")
        attempt.ended_at = datetime.utcnow()

        # Calculate duration for failed attempt
        if attempt.started_at and attempt.ended_at:
            attempt.duration_seconds = max(
                0,
                int(
                    (
                        attempt.ended_at - attempt.started_at
                    ).total_seconds()
                )
            )

        retryable = call.get("retryable", False)

        if retryable and attempt.attempt_number < 3:

            queue_item.status = "queued"
            queue_item.failure_reason = call.get("message")
            queue_item.completed_at = None

            db.commit()

            return {
                "queue_id": queue_item.id,
                "phone": queue_item.phone,
                "queue_status": queue_item.status,
                "attempt_id": attempt.id,
                "attempt_number": attempt.attempt_number,
                "attempt_status": attempt.status,
                "duration_seconds": attempt.duration_seconds,
                "retry": True,
                "failure_reason": attempt.failure_reason
            }

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
            "duration_seconds": attempt.duration_seconds,
            "retry": False,
            "failure_reason": attempt.failure_reason
        }

    # -------------------------------------------------
    # TELEPHONY SUCCESS
    # -------------------------------------------------

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

    if queue_item.status != "queued":
        return {
            "success": False,
            "message": (
                f"Call is not queued. "
                f"Current status: {queue_item.status}"
            )
        }

    previous_attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_id)
        .count()
    )

    attempt_number = previous_attempts + 1

    if attempt_number > 3:

        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = "Maximum call attempts reached"

        db.commit()

        return {
            "success": False,
            "message": "Maximum call attempts reached",
            "queue_id": queue_id,
            "queue_status": queue_item.status
        }

    queue_item.status = "calling"

    if queue_item.started_at is None:
        queue_item.started_at = datetime.utcnow()

    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=attempt_number,
        status="started",
        started_at=datetime.utcnow()
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    call = initiate_call(
        phone=queue_item.phone,
        queue_id=queue_item.id,
        attempt_id=attempt.id
    )

    # -------------------------------------------------
    # TELEPHONY FAILURE
    # -------------------------------------------------

    if not call.get("success"):

        attempt.status = "failed"
        attempt.failure_reason = call.get("message")
        attempt.ended_at = datetime.utcnow()

        # Calculate duration for failed attempt
        if attempt.started_at and attempt.ended_at:
            attempt.duration_seconds = max(
                0,
                int(
                    (
                        attempt.ended_at - attempt.started_at
                    ).total_seconds()
                )
            )

        retryable = call.get("retryable", False)

        if retryable and attempt.attempt_number < 3:

            queue_item.status = "queued"
            queue_item.failure_reason = call.get("message")
            queue_item.completed_at = None

            db.commit()

            return {
                "success": False,
                "queue_id": queue_item.id,
                "phone": queue_item.phone,
                "queue_status": queue_item.status,
                "attempt_id": attempt.id,
                "attempt_number": attempt.attempt_number,
                "attempt_status": attempt.status,
                "duration_seconds": attempt.duration_seconds,
                "retry": True,
                "failure_reason": attempt.failure_reason
            }

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
            "duration_seconds": attempt.duration_seconds,
            "retry": False,
            "failure_reason": attempt.failure_reason
        }

    # -------------------------------------------------
    # TELEPHONY SUCCESS
    # -------------------------------------------------

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
    db: Session,
    ended_at: datetime | None = None,
    duration_seconds: int | None = None
):
    """
    Process the result of a call attempt.

    Retryable results:
        no_answer
        busy
        failed

    Maximum attempts:
        3
    """

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

    if attempt.queue_id != queue_id:
        return {
            "success": False,
            "message": "Call attempt does not belong to this queue"
        }

    attempt.status = status
    attempt.result = result
    attempt.failure_reason = failure_reason

    # Use actual provider end time when available.
    attempt.ended_at = ended_at or datetime.utcnow()

    # Prefer provider-reported duration.
    if duration_seconds is not None:
        attempt.duration_seconds = max(
            0,
            int(duration_seconds)
        )

    # Fallback for manual/internal call-result requests.
    elif attempt.started_at and attempt.ended_at:
        attempt.duration_seconds = max(
            0,
            int(
                (
                    attempt.ended_at - attempt.started_at
                ).total_seconds()
            )
        )

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
            "started_at": attempt.started_at,
            "ended_at": attempt.ended_at,
            "duration_seconds": attempt.duration_seconds,
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

    if (
        status in retryable_results
        or result in retryable_results
    ):

        if attempt.attempt_number < 3:

            queue_item.status = "queued"
            queue_item.completed_at = None
            queue_item.failure_reason = (
                failure_reason
                or result
                or status
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
                "failure_reason": attempt.failure_reason,
                "started_at": attempt.started_at,
                "ended_at": attempt.ended_at,
                "duration_seconds": attempt.duration_seconds,
                "completed_at": queue_item.completed_at,
                "retry": True,
                "next_attempt": attempt.attempt_number + 1
            }

        queue_item.status = "failed"
        queue_item.completed_at = datetime.utcnow()
        queue_item.failure_reason = (
            failure_reason
            or result
            or status
            or "Maximum call attempts reached"
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
            "started_at": attempt.started_at,
            "ended_at": attempt.ended_at,
            "duration_seconds": attempt.duration_seconds,
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
        "started_at": attempt.started_at,
        "ended_at": attempt.ended_at,
        "duration_seconds": attempt.duration_seconds,
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

    queue_item.callback_at = callback_at
    queue_item.callback_status = "scheduled"

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
    and automatically processed into a new call attempt.
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

        lead = (
            db.query(Lead)
            .filter(Lead.id == queue_item.lead_id)
            .first()
        )

        queue_item.status = "queued"
        queue_item.callback_status = "processing"

        db.commit()

        call_result = process_specific_call(
            queue_id=queue_item.id,
            db=db
        )

        crm_result = None

        # -------------------------------------------------
        # CALLBACK INITIATED
        # -------------------------------------------------

        if call_result.get("success"):

            queue_item.callback_at = None
            queue_item.callback_status = "completed"

            if lead and lead.zoho_lead_id:

                crm_result = update_lead_after_call(
                    zoho_lead_id=lead.zoho_lead_id,
                    outcome="callback_initiated",
                    sentiment="neutral",
                    summary=(
                        "Scheduled callback was initiated "
                        "by the dialer."
                    )
                )

            db.commit()
            db.refresh(queue_item)

        # -------------------------------------------------
        # CALLBACK RETRY
        # -------------------------------------------------

        elif call_result.get("retry"):

            queue_item.callback_status = "processing"

            if lead and lead.zoho_lead_id:

                crm_result = update_lead_after_call(
                    zoho_lead_id=lead.zoho_lead_id,
                    outcome="callback_retry",
                    sentiment="neutral",
                    summary=(
                        call_result.get("failure_reason")
                        or "Callback attempt failed and "
                           "will be retried."
                    )
                )

            db.commit()
            db.refresh(queue_item)

        # -------------------------------------------------
        # CALLBACK FAILED
        # -------------------------------------------------

        else:

            queue_item.callback_status = "failed"

            if lead and lead.zoho_lead_id:

                crm_result = update_lead_after_call(
                    zoho_lead_id=lead.zoho_lead_id,
                    outcome="callback_failed",
                    sentiment="neutral",
                    summary=(
                        call_result.get("failure_reason")
                        or "Scheduled callback could not "
                           "be initiated."
                    )
                )

            db.commit()
            db.refresh(queue_item)

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
            "duration_seconds": call_result.get(
                "duration_seconds"
            ),
            "retry": call_result.get("retry", False),
            "success": call_result.get("success", False),
            "crm": crm_result
        })

    return {
        "success": True,
        "processed_count": len(processed_callbacks),
        "callbacks": processed_callbacks
    }