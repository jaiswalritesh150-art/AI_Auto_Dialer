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
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(__file__)
                )
            )
        ),
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

# This is your verified phone number.
# Keep it only inside .env.
EXOTEL_TEST_TO = os.getenv("EXOTEL_TEST_TO")

EXOTEL_BASE_URL = "https://api.exotel.com"


# =====================================================
# INITIATE CALL
# =====================================================

def initiate_call(phone: str, queue_id: int, attempt_id: int):
    """
    Initiate an outbound call through Exotel.

    phone:
        Lead/customer phone number.

    EXOTEL_TEST_TO:
        Verified phone number used as the second leg
        during the initial API integration test.
    """

    if not phone:
        return {
            "success": False,
            "message": "Phone number is required",
            "retryable": False
        }

    if (
        not EXOTEL_API_KEY
        or not EXOTEL_API_TOKEN
        or not EXOTEL_ACCOUNT_SID
        or not EXOTEL_CALLER_ID
    ):
        return {
            "success": False,
            "message": "Exotel configuration is incomplete",
            "retryable": False
        }

    if not EXOTEL_TEST_TO:
        return {
            "success": False,
            "message": "EXOTEL_TEST_TO is not configured",
            "retryable": False
        }

    # -------------------------------------------------
    # EXOTEL OUTBOUND CALL ENDPOINT
    # -------------------------------------------------

    exotel_url = (
        f"{EXOTEL_BASE_URL}"
        f"/v1/Accounts/{EXOTEL_ACCOUNT_SID}"
        f"/Calls/connect"
    )

    # -------------------------------------------------
    # EXOTEL PARAMETERS
    # -------------------------------------------------

    payload = {
        "From": phone,
        "To": EXOTEL_TEST_TO,
        "CallerId": EXOTEL_CALLER_ID
    }

    # -------------------------------------------------
    # MAKE ACTUAL API REQUEST
    # -------------------------------------------------

    try:
        response = requests.post(
            exotel_url,
            auth=(EXOTEL_API_KEY, EXOTEL_API_TOKEN),
            data=payload,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        # Try JSON first
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if response.ok:
            call_id = None

            # Exotel normally returns Call.Sid
            if isinstance(response_data, dict):
                call_info = response_data.get("Call", {})

                if isinstance(call_info, dict):
                    call_id = call_info.get("Sid")

            if not call_id:
                call_id = f"CALL-{uuid4().hex[:10].upper()}"

            return {
                "success": True,
                "provider": "exotel",
                "mode": "live",
                "call_id": call_id,
                "queue_id": queue_id,
                "attempt_id": attempt_id,
                "phone": phone,
                "to": EXOTEL_TEST_TO,
                "caller_id": EXOTEL_CALLER_ID,
                "status": "initiated",
                "http_status": response.status_code,
                "response": response_data,
                "initiated_at": datetime.utcnow()
            }

        # -------------------------------------------------
        # EXOTEL API ERROR
        # -------------------------------------------------

        return {
            "success": False,
            "provider": "exotel",
            "mode": "live",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "http_status": response.status_code,
            "message": "Exotel API request failed",
            "retryable": response.status_code >= 500,
            "response": response_data
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "provider": "exotel",
            "mode": "live",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "message": "Unable to connect to Exotel",
            "retryable": True,
            "error": str(exc)
        }


# =====================================================
# GET CALL STATUS
# =====================================================

def get_call_status(call_id: str):
    """
    Placeholder for real Exotel call-status integration.
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
    Placeholder for real Exotel call termination.
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