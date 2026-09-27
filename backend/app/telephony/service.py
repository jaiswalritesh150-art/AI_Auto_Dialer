from datetime import datetime
from uuid import uuid4
import os

import requests
from dotenv import load_dotenv

# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

load_dotenv(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".env"
    )
)
# =====================================================
# EXOTEL CONFIGURATION
# =====================================================

EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID")
EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID")

EXOTEL_BASE_URL = "https://api.in.exotel.com"


# =====================================================
# INITIATE CALL
# =====================================================

def initiate_call(phone: str, queue_id: int, attempt_id: int):
    """
    Prepare an outbound call through Exotel.

    The actual Exotel API call will be enabled after
    ExoPhone and Call Flow configuration is complete.
    """

    if not phone:
        return {
            "success": False,
            "message": "Phone number is required"
        }

    if (
        not EXOTEL_API_KEY
        or not EXOTEL_API_TOKEN
        or not EXOTEL_ACCOUNT_SID
        or not EXOTEL_CALLER_ID
    ):
        return {
            "success": False,
            "message": "Exotel configuration is incomplete"
        }

    # Exotel outbound call endpoint
    exotel_url = (
        f"{EXOTEL_BASE_URL}"
        f"/v1/Accounts/{EXOTEL_ACCOUNT_SID}"
        f"/Calls/connect"
    )

    # Request headers
    headers = {
        "Accept": "application/json"
    }

    # Exotel call parameters
    payload = {
        "From": phone,
        "CallerId": EXOTEL_CALLER_ID
    }

    # -------------------------------------------------
    # TEMPORARY SAFE MODE
    # -------------------------------------------------
    # Do not send the request yet because the Exotel
    # account / ExoPhone flow configuration is not
    # confirmed as active.
    #
    # The URL, headers and payload are prepared so that
    # the real API integration can be enabled safely.
    # -------------------------------------------------

    call_id = f"CALL-{uuid4().hex[:10].upper()}"

    return {
        "success": True,
        "provider": "exotel",
        "mode": "prepared",
        "call_id": call_id,
        "queue_id": queue_id,
        "attempt_id": attempt_id,
        "phone": phone,
        "caller_id": EXOTEL_CALLER_ID,
        "status": "ready",
        "exotel_url": exotel_url,
        "payload": payload,
        "initiated_at": datetime.utcnow()
    }


# =====================================================
# GET CALL STATUS
# =====================================================

def get_call_status(call_id: str):
    """
    Get the current status of an Exotel call.

    Real call-status API integration will be added
    after the outbound call flow is active.
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

    Real Exotel call termination will be added after
    the outbound call integration is active.
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