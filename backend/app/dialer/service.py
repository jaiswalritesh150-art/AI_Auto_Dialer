
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import CallQueue, CallAttempt, Lead
from app.telephony.service import initiate_call
from app.crm.service import update_lead_after_call


MAX_ATTEMPTS = 3
CALLBACK_RETRY_DELAY_MINUTES = 5
STALE_ATTEMPT_TIMEOUT_SECONDS = 7200


def _utcnow():
    """Return UTC datetime without tzinfo for existing DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_utc_naive(value: datetime) -> datetime:
    """Normalize aware or naive datetimes to naive UTC."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _safe_crm_update(lead, outcome, summary):
    """CRM failures must not crash the callback worker."""
    if not lead or not lead.zoho_lead_id:
        return None

    try:
        return update_lead_after_call(
            zoho_lead_id=lead.zoho_lead_id,
            outcome=outcome,
            sentiment="neutral",
            summary=summary
        )
    except Exception as exc:
        return {
            "success": False,
            "message": f"CRM update failed: {str(exc)}"
        }


def _create_attempt(queue_item, db):
    """Create and persist the next attempt before contacting telephony."""
    previous_attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.queue_id == queue_item.id)
        .count()
    )

    attempt_number = previous_attempts + 1

    if attempt_number > MAX_ATTEMPTS:
        queue_item.status = "failed"
        queue_item.completed_at = _utcnow()
        queue_item.failure_reason = "Maximum call attempts reached"
        db.commit()

        return None, {
            "success": False,
            "queue_id": queue_item.id,
            "queue_status": "failed",
            "message": "Maximum call attempts reached"
        }

    now = _utcnow()

    queue_item.status = "calling"
    queue_item.failure_reason = None

    if queue_item.started_at is None:
        queue_item.started_at = now

    attempt = CallAttempt(
        queue_id=queue_item.id,
        attempt_number=attempt_number,
        status="started",
        started_at=now
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return attempt, None


def _initiate_attempt(queue_item, attempt, db):
    """Initiate the provider call and persist its result."""

    try:
        call = initiate_call(
            phone=queue_item.phone,
            queue_id=queue_item.id,
            attempt_id=attempt.id
        )
    except Exception as exc:
        # An exception may happen after the provider accepted the request.
        # Do not automatically retry an uncertain provider outcome.
        now = _utcnow()
        attempt.status = "failed"
        attempt.failure_reason = (
            f"Telephony initiation outcome uncertain: {str(exc)}"
        )
        attempt.ended_at = now
        attempt.duration_seconds = 0

        queue_item.status = "failed"
        queue_item.completed_at = now
        queue_item.failure_reason = attempt.failure_reason

        db.commit()

        return {
            "success": False,
            "queue_id": queue_item.id,
            "phone": queue_item.phone,
            "queue_status": queue_item.status,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "duration_seconds": 0,
            "retry": False,
            "failure_reason": attempt.failure_reason
        }

    if not isinstance(call, dict):
        call = {
            "success": False,
            "message": "Invalid telephony provider response",
            "retryable": False
        }

    if not call.get("success"):
        now = _utcnow()
        attempt.status = "failed"
        attempt.failure_reason = call.get("message")
        attempt.ended_at = now
        attempt.duration_seconds = 0

        retry = (
            bool(call.get("retryable", False))
            and attempt.attempt_number < MAX_ATTEMPTS
        )

        if retry:
            queue_item.status = "queued"
            queue_item.completed_at = None
            queue_item.failure_reason = call.get("message")
        else:
            queue_item.status = "failed"
            queue_item.completed_at = now
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
            "duration_seconds": 0,
            "retry": retry,
            "failure_reason": attempt.failure_reason
        }

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
# QUEUE LEAD
# =====================================================

def queue_lead(lead, db: Session):
    queue_item = CallQueue(
        lead_id=lead.id,
        phone=lead.phone,
        status="queued",
        queued_at=_utcnow()
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
        "queued_at": queue_item.queued_at
    }


# =====================================================
# PROCESS NEXT CALL
# =====================================================

def process_next_call(db: Session):
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.status == "queued")
        .order_by(CallQueue.queued_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )

    if not queue_item:
        return None

    attempt, error = _create_attempt(queue_item, db)

    if error:
        return error

    return _initiate_attempt(queue_item, attempt, db)


# =====================================================
# PROCESS SPECIFIC CALL
# =====================================================

def process_specific_call(queue_id: int, db: Session):
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .with_for_update(skip_locked=True)
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
                f"Call is not queued. Current status: "
                f"{queue_item.status}"
            )
        }

    attempt, error = _create_attempt(queue_item, db)

    if error:
        return error

    return _initiate_attempt(queue_item, attempt, db)


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

    # Ignore duplicate terminal callbacks.
    if attempt.ended_at is not None:
        return {
            "success": True,
            "message": "Call attempt already finalized",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "attempt_status": attempt.status,
            "queue_status": queue_item.status,
            "duplicate": True
        }

    attempt.status = status
    attempt.result = result
    attempt.failure_reason = failure_reason
    attempt.ended_at = _to_utc_naive(ended_at) if ended_at else _utcnow()

    if duration_seconds is not None:
        attempt.duration_seconds = max(0, int(duration_seconds))
    elif attempt.started_at:
        attempt.duration_seconds = max(
            0,
            int((attempt.ended_at - attempt.started_at).total_seconds())
        )

    if status == "completed":
        queue_item.status = "completed"
        queue_item.completed_at = _utcnow()
        queue_item.failure_reason = None

    elif status in {"no_answer", "busy", "failed"} or result in {
        "no_answer", "busy", "failed"
    }:
        if attempt.attempt_number < MAX_ATTEMPTS:
            queue_item.status = "queued"
            queue_item.completed_at = None
            queue_item.failure_reason = (
                failure_reason or result or status
            )
        else:
            queue_item.status = "failed"
            queue_item.completed_at = _utcnow()
            queue_item.failure_reason = (
                failure_reason or result or status
                or "Maximum call attempts reached"
            )

    else:
        queue_item.status = status
        queue_item.completed_at = _utcnow()
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
        "retry": queue_item.status == "queued",
        "next_attempt": (
            attempt.attempt_number + 1
            if queue_item.status == "queued"
            else None
        )
    }


# =====================================================
# RECOVER STALE CALL ATTEMPTS
# =====================================================

def recover_stale_call_attempts(
    db: Session,
    timeout_seconds: int = STALE_ATTEMPT_TIMEOUT_SECONDS
):
    cutoff_time = _utcnow() - timedelta(seconds=timeout_seconds)

    stale_attempts = (
        db.query(CallAttempt)
        .filter(
            CallAttempt.status.in_(["started", "initiated"]),
            CallAttempt.started_at.isnot(None),
            CallAttempt.started_at < cutoff_time,
            CallAttempt.ended_at.is_(None)
        )
        .with_for_update(skip_locked=True)
        .all()
    )

    recovered = []

    for attempt in stale_attempts:
        queue_item = (
            db.query(CallQueue)
            .filter(CallQueue.id == attempt.queue_id)
            .first()
        )

        ended_at = _utcnow()

        attempt.status = "failed"
        attempt.result = "failed"
        attempt.failure_reason = (
            "Call attempt timed out or became stale"
        )
        attempt.ended_at = ended_at

        if attempt.started_at:
            duration = max(
                0,
                int((ended_at - attempt.started_at).total_seconds())
            )
            attempt.duration_seconds = min(duration, timeout_seconds)

        retry = False
        queue_status = None

        if queue_item:
            # Do not overwrite a queue item that has already moved
            # to another state, such as callback_scheduled.
            if queue_item.status == "calling":
                if attempt.attempt_number < MAX_ATTEMPTS:
                    queue_item.status = "queued"
                    queue_item.completed_at = None
                    queue_item.failure_reason = (
                        "Previous call attempt timed out"
                    )
                    retry = True
                else:
                    queue_item.status = "failed"
                    queue_item.completed_at = ended_at
                    queue_item.failure_reason = (
                        "Maximum call attempts reached after timeout"
                    )

            queue_status = queue_item.status

        recovered.append({
            "attempt_id": attempt.id,
            "queue_id": attempt.queue_id,
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.status,
            "queue_status": queue_status,
            "duration_seconds": attempt.duration_seconds,
            "retry": retry
        })

    if stale_attempts:
        db.commit()

    return {
        "success": True,
        "recovered_count": len(recovered),
        "attempts": recovered
    }


# =====================================================
# SCHEDULE CALLBACK
# =====================================================

def schedule_callback(
    queue_id: int,
    callback_at: datetime,
    db: Session
):
    queue_item = (
        db.query(CallQueue)
        .filter(CallQueue.id == queue_id)
        .with_for_update()
        .first()
    )

    if not queue_item:
        return {
            "success": False,
            "message": "Call queue item not found"
        }

    callback_at = _to_utc_naive(callback_at)

    if callback_at <= _utcnow():
        return {
            "success": False,
            "message": "Callback time must be in the future"
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
    Process due callbacks one at a time.

    Row locking prevents two callback workers from claiming
    the same scheduled callback simultaneously.

    Retryable initiation failures are rescheduled after
    CALLBACK_RETRY_DELAY_MINUTES.
    """

    stale_result = recover_stale_call_attempts(db=db)

    processed_callbacks = []

    while True:
        now = _utcnow()

        # Claim one due callback at a time. The row lock remains
        # held until process_specific_call commits its calling state.
        queue_item = (
            db.query(CallQueue)
            .filter(
                CallQueue.status == "callback_scheduled",
                CallQueue.callback_status == "scheduled",
                CallQueue.callback_at.isnot(None),
                CallQueue.callback_at <= now
            )
            .order_by(CallQueue.callback_at.asc())
            .with_for_update(skip_locked=True)
            .first()
        )

        if not queue_item:
            break

        queue_id = queue_item.id
        callback_time = queue_item.callback_at

        lead = (
            db.query(Lead)
            .filter(Lead.id == queue_item.lead_id)
            .first()
        )

        # Keep this change in the same transaction. Do not commit
        # here: process_specific_call will claim the queue item
        # and persist status="calling" before releasing the lock.
        queue_item.status = "queued"
        queue_item.callback_status = "processing"

        try:
            call_result = process_specific_call(
                queue_id=queue_id,
                db=db
            )

        except Exception as exc:
            db.rollback()

            queue_item = (
                db.query(CallQueue)
                .filter(CallQueue.id == queue_id)
                .with_for_update()
                .first()
            )

            if queue_item:
                queue_item.status = "failed"
                queue_item.callback_status = "failed"
                queue_item.callback_at = None
                queue_item.completed_at = _utcnow()
                queue_item.failure_reason = (
                    f"Callback processing error: {str(exc)}"
                )
                db.commit()

            crm_result = _safe_crm_update(
                lead,
                "callback_failed",
                "Callback processing failed. Manual review is required."
            )

            processed_callbacks.append({
                "queue_id": queue_id,
                "callback_at": callback_time,
                "callback_status": "failed",
                "queue_status": "failed",
                "success": False,
                "retry": False,
                "failure_reason": str(exc),
                "crm": crm_result
            })

            continue

        # Reload after process_specific_call's internal commit.
        queue_item = (
            db.query(CallQueue)
            .filter(CallQueue.id == queue_id)
            .first()
        )

        if not queue_item:
            continue

        crm_result = None

        if call_result.get("success"):
            # The callback call has been initiated. The actual
            # conversation outcome will arrive through provider events.
            queue_item.callback_at = None
            queue_item.callback_status = "completed"

            crm_result = _safe_crm_update(
                lead,
                "callback_initiated",
                "Scheduled callback was initiated by the dialer."
            )

        elif call_result.get("retry"):
            # IMPORTANT FIX:
            # Reschedule instead of leaving callback_status="processing".
            next_callback_time = (
                _utcnow()
                + timedelta(minutes=CALLBACK_RETRY_DELAY_MINUTES)
            )

            queue_item.status = "callback_scheduled"
            queue_item.callback_status = "scheduled"
            queue_item.callback_at = next_callback_time
            queue_item.completed_at = None

            crm_result = _safe_crm_update(
                lead,
                "callback_retry",
                (
                    call_result.get("failure_reason")
                    or "Callback initiation failed; retry scheduled."
                )
            )

        else:
            queue_item.callback_status = "failed"
            queue_item.callback_at = None

            crm_result = _safe_crm_update(
                lead,
                "callback_failed",
                (
                    call_result.get("failure_reason")
                    or "Scheduled callback could not be initiated."
                )
            )

        db.commit()
        db.refresh(queue_item)

        processed_callbacks.append({
            "queue_id": queue_item.id,
            "callback_at": queue_item.callback_at,
            "callback_status": queue_item.callback_status,
            "queue_status": queue_item.status,
            "attempt_id": call_result.get("attempt_id"),
            "attempt_number": call_result.get("attempt_number"),
            "attempt_status": call_result.get("attempt_status"),
            "duration_seconds": call_result.get("duration_seconds"),
            "retry": call_result.get("retry", False),
            "success": call_result.get("success", False),
            "failure_reason": call_result.get("failure_reason"),
            "crm": crm_result
        })

    return {
        "success": True,
        "stale_recovered_count": stale_result.get(
            "recovered_count", 0
        ),
        "stale_attempts": stale_result.get("attempts", []),
        "processed_count": len(processed_callbacks),
        "callbacks": processed_callbacks
    }
