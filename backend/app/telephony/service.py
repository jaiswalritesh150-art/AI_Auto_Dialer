from datetime import datetime
from uuid import uuid4


# =====================================================
# INITIATE CALL
# =====================================================

def initiate_call(phone: str, queue_id: int, attempt_id: int):
    """
    Start a telephony call.

    Currently this is a simulated provider layer.
    A real provider such as Twilio/Exotel can be
    connected here later.
    """

    if not phone:
        return {
            "success": False,
            "message": "Phone number is required"
        }

    call_id = f"CALL-{uuid4().hex[:10].upper()}"

    return {
        "success": True,
        "provider": "simulated",
        "call_id": call_id,
        "queue_id": queue_id,
        "attempt_id": attempt_id,
        "phone": phone,
        "status": "initiated",
        "initiated_at": datetime.utcnow()
    }


# =====================================================
# GET CALL STATUS
# =====================================================

def get_call_status(call_id: str):
    """
    Get the current status of a call.

    Simulated for now.
    """

    if not call_id:
        return {
            "success": False,
            "message": "Call ID is required"
        }

    return {
        "success": True,
        "provider": "simulated",
        "call_id": call_id,
        "status": "in_progress"
    }


# =====================================================
# END CALL
# =====================================================

def end_call(call_id: str):
    """
    End an active call.

    Simulated for now.
    """

    if not call_id:
        return {
            "success": False,
            "message": "Call ID is required"
        }

    return {
        "success": True,
        "provider": "simulated",
        "call_id": call_id,
        "status": "completed",
        "ended_at": datetime.utcnow()
    }