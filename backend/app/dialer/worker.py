from datetime import datetime
from app.database import SessionLocal
from app.models import CallQueue, CallAttempt


def process_queue():
    db = SessionLocal()

    try:
        queue_item = (
            db.query(CallQueue)
            .filter(CallQueue.status == "queued")
            .order_by(CallQueue.id.asc())
            .first()
        )

        if not queue_item:
            print("No queued calls found.")
            return

        print("\n" + "=" * 50)
        print("DIALER WORKER")
        print("=" * 50)

        print(f"Queue ID: {queue_item.id}")
        print(f"Lead ID: {queue_item.lead_id}")
        print(f"Phone: {queue_item.phone}")


        attempt_number = (
            db.query(CallAttempt)
            .filter(CallAttempt.queue_id == queue_item.id)
            .count()
            + 1
        )

        call_attempt = CallAttempt(
            queue_id=queue_item.id,
            attempt_number=attempt_number,
            status="started",
            started_at=datetime.utcnow()
        )

        db.add(call_attempt)
        db.commit()
        db.refresh(call_attempt)

        print(f"\nCall Attempt ID: {call_attempt.id}")
        print(f"Attempt Number: {call_attempt.attempt_number}")

        queue_item.status = "calling"
        queue_item.started_at = datetime.utcnow()

        call_attempt.status = "calling"

        db.commit()

        print("\nCall status: calling")

        # Actual calling provider will be connected later.

        queue_item.status = "completed"
        queue_item.completed_at = datetime.utcnow()

        call_attempt.status = "completed"
        call_attempt.ended_at = datetime.utcnow()
        call_attempt.result = "simulated_success"

        db.commit()

        print("Call status: completed")
        print("Call result: simulated_success")

        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"Worker error: {e}")

    finally:
        db.close()

