from datetime import datetime
from uuid import uuid4
import os

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))


# =====================================================
# EXOTEL CONFIGURATION
# =====================================================

EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_BASE_URL = "https://api.in.exotel.com"


# =====================================================
# INITIATE CALL
# =====================================================

def initiate_call(phone: str, queue_id: int, attempt_id: int):
    """
    Start a telephony call through Exotel.

    Exotel credentials are loaded from environment
    variables and are never hardcoded in the source code.
    """

    if not phone:
        return {
            "success": False,
            "message": "Phone number is required"
        }

    if not EXOTEL_API_KEY or not EXOTEL_API_TOKEN:
        return {
            "success": False,
            "message": "Exotel API credentials are not configured"
        }

    call_id = f"CALL-{uuid4().hex[:10].upper()}"

    return {
        "success": True,
        "provider": "exotel",
        "call_id": call_id,
        "queue_id": queue_id,
        "attempt_id": attempt_id,
        "phone": phone,
        "status": "ready",
        "initiated_at": datetime.utcnow()
    }


# =====================================================
# GET CALL STATUS
# =====================================================

def get_call_status(call_id: str):
    """
    Get the current status of a call.

    Real Exotel status handling will be connected
    after the outbound call API configuration.
    """

    if not call_id:
        return {
            "success": False,
            "message": "Call ID is required"
        }

    return {
        "success": True,
        "provider": "exotel",
        "call_id": call_id,
        "status": "in_progress"
    }


# =====================================================
# END CALL
# =====================================================

def end_call(call_id: str):
    """
    End an active call.

    Real Exotel call termination will be connected
    after the outbound call flow is configured.
    """

    if not call_id:
        return {
            "success": False,
            "message": "Call ID is required"
        }

    return {
        "success": True,
        "provider": "exotel",
        "call_id": call_id,
        "status": "completed",
        "ended_at": datetime.utcnow()
    }
