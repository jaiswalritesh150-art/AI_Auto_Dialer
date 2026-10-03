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

# Public webhook URL for Exotel call status callbacks.
#
# Example:
# https://your-domain.com/api/v1/webhooks/exotel/call-status
#
# Do NOT put localhost here because Exotel cannot directly
# reach your local machine.
EXOTEL_STATUS_CALLBACK_URL = os.getenv(
    "EXOTEL_STATUS_CALLBACK_URL"
)

EXOTEL_BASE_URL = "https://api.exotel.com"

# Telephony execution mode.
# "live"  -> real Exotel API
# "mock"  -> simulated call for development/testing
TELEPHONY_MODE = os.getenv("TELEPHONY_MODE", "live").lower()


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

    EXOTEL_STATUS_CALLBACK_URL:
        Public endpoint where Exotel sends terminal
        call status updates.
    """

    # -------------------------------------------------
    # MOCK TELEPHONY MODE
    # -------------------------------------------------

    if TELEPHONY_MODE == "mock":

        mock_call_id = (
            f"MOCK-{uuid4().hex[:10].upper()}"
        )

        return {
            "success": True,
            "provider": "mock",
            "mode": "mock",
            "call_id": mock_call_id,
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "phone": phone,
            "to": phone,
            "caller_id": "MOCK_CALLER",
            "status": "initiated",
            "http_status": 200,
            "response": {
                "message": "Mock call initiated successfully"
            },
            "status_callback": None,
            "initiated_at": datetime.utcnow()
        }

    # -------------------------------------------------
    # VALIDATE PHONE
    # -------------------------------------------------

    if not phone:
        return {
            "success": False,
            "message": "Phone number is required",
            "retryable": False
        }

    # -------------------------------------------------
    # VALIDATE EXOTEL CONFIGURATION
    # -------------------------------------------------

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

    # -------------------------------------------------
    # VALIDATE TEST NUMBER
    # -------------------------------------------------

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
    # STATUS CALLBACK
    # -------------------------------------------------

    if EXOTEL_STATUS_CALLBACK_URL:
        payload["StatusCallback"] = EXOTEL_STATUS_CALLBACK_URL
        payload["StatusCallbackEvents[]"] = "terminal"

    # -------------------------------------------------
    # MAKE ACTUAL API REQUEST
    # -------------------------------------------------

    try:
        response = requests.post(
            exotel_url,
            auth=(
                EXOTEL_API_KEY,
                EXOTEL_API_TOKEN
            ),
            data=payload,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        # -------------------------------------------------
        # PARSE RESPONSE
        # -------------------------------------------------

        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if response.ok:

            call_id = None

            # Exotel normally returns:
            #
            # {
            #   "Call": {
            #       "Sid": "..."
            #   }
            # }
            #
            if isinstance(response_data, dict):

                call_info = response_data.get(
                    "Call",
                    {}
                )

                if isinstance(call_info, dict):
                    call_id = call_info.get("Sid")

            # -------------------------------------------------
            # FALLBACK CALL ID
            # -------------------------------------------------

            if not call_id:
                call_id = (
                    f"CALL-{uuid4().hex[:10].upper()}"
                )

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
                "status_callback": EXOTEL_STATUS_CALLBACK_URL,
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

    # -------------------------------------------------
    # NETWORK ERROR
    # -------------------------------------------------

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
    Fetch call details from Exotel.

    This acts as a fallback if the status callback
    is delayed or unavailable.
    """

    # -------------------------------------------------
    # VALIDATE CALL ID
    # -------------------------------------------------

    if not call_id:
        return {
            "success": False,
            "provider": "exotel",
            "message": "Call ID is required"
        }

    # -------------------------------------------------
    # VALIDATE CONFIGURATION
    # -------------------------------------------------

    if (
        not EXOTEL_API_KEY
        or not EXOTEL_API_TOKEN
        or not EXOTEL_ACCOUNT_SID
    ):
        return {
            "success": False,
            "provider": "exotel",
            "message": "Exotel configuration is incomplete"
        }

    # -------------------------------------------------
    # EXOTEL CALL DETAILS ENDPOINT
    # -------------------------------------------------

    exotel_url = (
        f"{EXOTEL_BASE_URL}"
        f"/v1/Accounts/{EXOTEL_ACCOUNT_SID}"
        f"/Calls.json"
    )

    params = {
        "Sid": call_id
    }

    # -------------------------------------------------
    # REQUEST
    # -------------------------------------------------

    try:

        response = requests.get(
            exotel_url,
            auth=(
                EXOTEL_API_KEY,
                EXOTEL_API_TOKEN
            ),
            params=params,
            headers={
                "Accept": "application/json"
            },
            timeout=30
        )

        # -------------------------------------------------
        # PARSE RESPONSE
        # -------------------------------------------------

        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if response.ok:

            return {
                "success": True,
                "provider": "exotel",
                "call_id": call_id,
                "http_status": response.status_code,
                "response": response_data
            }

        # -------------------------------------------------
        # API ERROR
        # -------------------------------------------------

        return {
            "success": False,
            "provider": "exotel",
            "call_id": call_id,
            "http_status": response.status_code,
            "message": "Unable to fetch call status from Exotel",
            "retryable": response.status_code >= 500,
            "response": response_data
        }

    # -------------------------------------------------
    # NETWORK ERROR
    # -------------------------------------------------

    except requests.RequestException as exc:

        return {
            "success": False,
            "provider": "exotel",
            "call_id": call_id,
            "message": "Unable to connect to Exotel",
            "retryable": True,
            "error": str(exc)
        }


# =====================================================
# END CALL
# =====================================================

def end_call(call_id: str):
    """
    End-call placeholder.

    The current outbound integration primarily relies
    on Exotel's call lifecycle and terminal callback.
    """

    # -------------------------------------------------
    # VALIDATE CALL ID
    # -------------------------------------------------

    if not call_id:
        return {
            "success": False,
            "provider": "exotel",
            "message": "Call ID is required"
        }

    # -------------------------------------------------
    # IMPORTANT
    # -------------------------------------------------
    #
    # We are not pretending that the call was actually
    # terminated at Exotel.
    #
    # Actual terminal state should come from Exotel's
    # status callback / Call Details API.
    #

    return {
        "success": False,
        "provider": "exotel",
        "call_id": call_id,
        "message": (
            "Direct call termination is not implemented. "
            "Use Exotel terminal status callback or "
            "Call Details API."
        ),
        "retryable": False
    }