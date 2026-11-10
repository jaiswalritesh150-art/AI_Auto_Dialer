
from datetime import datetime, timezone
from uuid import uuid4
import os
import re

import requests
from dotenv import load_dotenv


# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

load_dotenv(os.path.join(BASE_DIR, ".env"))


# =====================================================
# EXOTEL CONFIGURATION
# =====================================================

EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_ACCOUNT_SID = os.getenv("EXOTEL_ACCOUNT_SID")
EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID")

# India region by default. Override only if your account
# is hosted in another Exotel region.
EXOTEL_BASE_URL = os.getenv(
    "EXOTEL_BASE_URL",
    "https://api.in.exotel.com"
).rstrip("/")

# Public WebSocket endpoint for Exotel AgentStream.
# Example: wss://your-domain.com/api/v1/telephony/agentstream
EXOTEL_STREAM_URL = os.getenv("EXOTEL_STREAM_URL")

# Public HTTP endpoint for Exotel status callbacks.
EXOTEL_STATUS_CALLBACK_URL = os.getenv(
    "EXOTEL_STATUS_CALLBACK_URL"
)

# Keep mock as the safe default. Set live explicitly only
# after credentials, stream endpoint and account are verified.
TELEPHONY_MODE = os.getenv(
    "TELEPHONY_MODE",
    "mock"
).strip().lower()

EXOTEL_RECORD_CALLS = os.getenv(
    "EXOTEL_RECORD_CALLS",
    "false"
).strip().lower() == "true"

EXOTEL_TIME_LIMIT = int(
    os.getenv("EXOTEL_TIME_LIMIT", "1800")
)

REQUEST_TIMEOUT = 30


# =====================================================
# HELPERS
# =====================================================

def utc_now():
    return datetime.now(timezone.utc)


def is_valid_e164(phone: str) -> bool:
    """Validate an international E.164 phone number."""
    if not phone:
        return False

    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", phone.strip()))


def exotel_configuration_error():
    """Return a configuration error, or None if valid."""

    required = {
        "EXOTEL_API_KEY": EXOTEL_API_KEY,
        "EXOTEL_API_TOKEN": EXOTEL_API_TOKEN,
        "EXOTEL_ACCOUNT_SID": EXOTEL_ACCOUNT_SID,
        "EXOTEL_CALLER_ID": EXOTEL_CALLER_ID,
        "EXOTEL_STREAM_URL": EXOTEL_STREAM_URL,
    }

    missing = [
        name for name, value in required.items()
        if not value
    ]

    if missing:
        return (
            "Missing Exotel configuration: "
            + ", ".join(missing)
        )

    if not EXOTEL_STREAM_URL.startswith("wss://"):
        return "EXOTEL_STREAM_URL must use a public wss:// URL"

    if len(EXOTEL_STREAM_URL) > 600:
        return "EXOTEL_STREAM_URL must not exceed 600 characters"

    return None


def exotel_calls_url():
    return (
        f"{EXOTEL_BASE_URL}/v1/Accounts/"
        f"{EXOTEL_ACCOUNT_SID}/Calls"
    )


# =====================================================
# INITIATE OUTBOUND AI CALL
# =====================================================

def initiate_call(
    phone: str,
    queue_id: int,
    attempt_id: int
):
    """
    Initiate an outbound AI call using Exotel Connect Voice AI.

    Exotel calls the customer number in `From`, displays
    the ExoPhone in `CallerId`, and connects the answered
    call to the public bidirectional AgentStream WebSocket.

    Important:
    This function starts the telephony call. It does not
    implement the AgentStream WebSocket server itself.
    """

    # -------------------------------------------------
    # MOCK MODE
    # -------------------------------------------------

    if TELEPHONY_MODE == "mock":

        if not phone:
            return {
                "success": False,
                "provider": "mock",
                "message": "Phone number is required",
                "retryable": False
            }

        return {
            "success": True,
            "provider": "mock",
            "mode": "mock",
            "call_id": f"MOCK-{uuid4().hex[:12].upper()}",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "phone": phone,
            "caller_id": "MOCK_CALLER",
            "status": "initiated",
            "http_status": 200,
            "response": {
                "message": "Mock call initiated successfully"
            },
            "initiated_at": utc_now()
        }

    # -------------------------------------------------
    # MODE VALIDATION
    # -------------------------------------------------

    if TELEPHONY_MODE != "live":
        return {
            "success": False,
            "message": (
                "Invalid TELEPHONY_MODE. "
                "Allowed values are mock or live."
            ),
            "retryable": False
        }

    # -------------------------------------------------
    # PHONE VALIDATION
    # -------------------------------------------------

    if not is_valid_e164(phone):
        return {
            "success": False,
            "provider": "exotel",
            "message": (
                "Invalid phone number. "
                "Use E.164 format, for example +919876543210."
            ),
            "retryable": False
        }

    # -------------------------------------------------
    # EXOTEL CONFIGURATION VALIDATION
    # -------------------------------------------------

    config_error = exotel_configuration_error()

    if config_error:
        return {
            "success": False,
            "provider": "exotel",
            "mode": "live",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "message": config_error,
            "retryable": False
        }

    # -------------------------------------------------
    # CONNECT VOICE AI API
    # -------------------------------------------------

    url = (
        f"{EXOTEL_BASE_URL}/v1/Accounts/"
        f"{EXOTEL_ACCOUNT_SID}/Calls/connect"
    )

    # Exotel Connect Voice AI API:
    # From       = customer number to dial
    # CallerId   = Exotel virtual number
    # StreamUrl  = public AgentStream WebSocket
    # StreamType = bidirectional

    payload = {
        "From": phone,
        "CallerId": EXOTEL_CALLER_ID,
        "StreamUrl": EXOTEL_STREAM_URL,
        "StreamType": "bidirectional",
        "TimeLimit": EXOTEL_TIME_LIMIT,
        "CustomField": f"queue:{queue_id};attempt:{attempt_id}",
        "Record": str(EXOTEL_RECORD_CALLS).lower()
    }

    if EXOTEL_STATUS_CALLBACK_URL:
        payload["StatusCallback"] = EXOTEL_STATUS_CALLBACK_URL
        payload["StatusCallbackEvents[]"] = "terminal"

    # -------------------------------------------------
    # API REQUEST
    # -------------------------------------------------

    try:
        response = requests.post(
            url,
            auth=(
                EXOTEL_API_KEY,
                EXOTEL_API_TOKEN
            ),
            data=payload,
            headers={
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )

        try:
            response_data = response.json()
        except ValueError:
            response_data = {
                "raw_response": response.text[:2000]
            }

        # -------------------------------------------------
        # API FAILURE
        # -------------------------------------------------

        if not response.ok:
            return {
                "success": False,
                "provider": "exotel",
                "mode": "live",
                "queue_id": queue_id,
                "attempt_id": attempt_id,
                "http_status": response.status_code,
                "message": "Exotel API request failed",
                "retryable": (
                    response.status_code == 408
                    or response.status_code == 429
                    or response.status_code >= 500
                ),
                "response": response_data
            }

        # -------------------------------------------------
        # EXTRACT REAL CALL SID
        # -------------------------------------------------

        call_info = {}

        if isinstance(response_data, dict):
            call_info = response_data.get("Call", {})

        call_id = (
            call_info.get("Sid")
            if isinstance(call_info, dict)
            else None
        )

        # Never generate a fake call ID for a live request.
        if not call_id:
            return {
                "success": False,
                "provider": "exotel",
                "mode": "live",
                "queue_id": queue_id,
                "attempt_id": attempt_id,
                "http_status": response.status_code,
                "message": (
                    "Exotel returned a successful HTTP response "
                    "but no Call SID was found."
                ),
                "retryable": False,
                "response": response_data
            }

        return {
            "success": True,
            "provider": "exotel",
            "mode": "live",
            "call_id": call_id,
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "phone": phone,
            "caller_id": EXOTEL_CALLER_ID,
            "status": (
                call_info.get("Status", "initiated")
                if isinstance(call_info, dict)
                else "initiated"
            ),
            "http_status": response.status_code,
            "response": response_data,
            "status_callback": EXOTEL_STATUS_CALLBACK_URL,
            "stream_url_configured": True,
            "initiated_at": utc_now()
        }

    # -------------------------------------------------
    # NETWORK / TIMEOUT ERROR
    # -------------------------------------------------

    except requests.Timeout:
        return {
            "success": False,
            "provider": "exotel",
            "mode": "live",
            "queue_id": queue_id,
            "attempt_id": attempt_id,
            "message": "Exotel request timed out",
            "retryable": True
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
    Fetch call details from Exotel.

    This is a fallback to the status callback.
    """

    if not call_id:
        return {
            "success": False,
            "provider": "exotel",
            "message": "Call ID is required",
            "retryable": False
        }

    if not all([
        EXOTEL_API_KEY,
        EXOTEL_API_TOKEN,
        EXOTEL_ACCOUNT_SID
    ]):
        return {
            "success": False,
            "provider": "exotel",
            "message": "Exotel configuration is incomplete",
            "retryable": False
        }

    url = f"{exotel_calls_url()}.json"

    try:
        response = requests.get(
            url,
            auth=(
                EXOTEL_API_KEY,
                EXOTEL_API_TOKEN
            ),
            params={
                "Sid": call_id
            },
            headers={
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )

        try:
            response_data = response.json()
        except ValueError:
            response_data = {
                "raw_response": response.text[:2000]
            }

        if not response.ok:
            return {
                "success": False,
                "provider": "exotel",
                "call_id": call_id,
                "http_status": response.status_code,
                "message": "Unable to fetch call status from Exotel",
                "retryable": (
                    response.status_code == 408
                    or response.status_code == 429
                    or response.status_code >= 500
                ),
                "response": response_data
            }

        return {
            "success": True,
            "provider": "exotel",
            "call_id": call_id,
            "http_status": response.status_code,
            "response": response_data
        }

    except requests.Timeout:
        return {
            "success": False,
            "provider": "exotel",
            "call_id": call_id,
            "message": "Exotel status request timed out",
            "retryable": True
        }

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
    Call termination is intentionally not implemented here.

    Do not mark a call as ended locally and claim that
    Exotel terminated it. The actual termination mechanism
    must be implemented against the enabled Exotel product
    and confirmed with its API documentation.

    Until then, use Exotel terminal callbacks to update
    the actual call state.
    """

    if not call_id:
        return {
            "success": False,
            "provider": "exotel",
            "message": "Call ID is required",
            "retryable": False
        }

    return {
        "success": False,
        "provider": "exotel",
        "call_id": call_id,
        "message": (
            "Direct call termination is not implemented. "
            "Wait for Exotel terminal callback."
        ),
        "retryable": False
    }
