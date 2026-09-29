import os
from datetime import datetime

import requests
from dotenv import load_dotenv


# Project root .env load karo
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_API_DOMAIN = os.getenv(
    "ZOHO_API_DOMAIN",
    "https://www.zohoapis.in"
)

ZOHO_ACCOUNTS_URL = "https://accounts.zoho.in/oauth/v2/token"


def get_zoho_access_token():
    """
    Generate a fresh Zoho access token using the stored refresh token.
    """

    if not all([
        ZOHO_CLIENT_ID,
        ZOHO_CLIENT_SECRET,
        ZOHO_REFRESH_TOKEN
    ]):
        return {
            "success": False,
            "message": "Zoho OAuth configuration is missing"
        }

    response = requests.post(
        ZOHO_ACCOUNTS_URL,
        data={
            "refresh_token": ZOHO_REFRESH_TOKEN,
            "client_id": ZOHO_CLIENT_ID,
            "client_secret": ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token"
        },
        timeout=20
    )

    if response.status_code != 200:
        return {
            "success": False,
            "message": "Failed to generate Zoho access token",
            "http_status": response.status_code,
            "details": response.text
        }

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        return {
            "success": False,
            "message": "Zoho access token missing in response",
            "details": data
        }

    return {
        "success": True,
        "access_token": access_token
    }


def update_lead_after_call(
    zoho_lead_id: str,
    outcome: str,
    sentiment: str,
    summary: str
):
    """
    Update a Zoho Lead after an AI dialer call.
    """

    if not zoho_lead_id:
        return {
            "success": False,
            "message": "Zoho Lead ID is required"
        }

    token_result = get_zoho_access_token()

    if not token_result["success"]:
        return token_result

    access_token = token_result["access_token"]

    description = (
        f"AI Auto Dialer Call Update\n"
        f"Outcome: {outcome}\n"
        f"Sentiment: {sentiment}\n"
        f"Summary: {summary}\n"
        f"Last Called At: {datetime.utcnow().isoformat()}Z"
    )

    url = (
        f"{ZOHO_API_DOMAIN}"
        f"/crm/v8/Leads/{zoho_lead_id}"
    )

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": [
            {
                "Description": description
            }
        ]
    }

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    try:
        response_data = response.json()
    except ValueError:
        response_data = {
            "raw_response": response.text
        }

    if response.status_code not in (200, 202):
        return {
            "success": False,
            "provider": "zoho",
            "zoho_lead_id": zoho_lead_id,
            "http_status": response.status_code,
            "message": "Zoho Lead update failed",
            "details": response_data
        }

    return {
        "success": True,
        "provider": "zoho",
        "zoho_lead_id": zoho_lead_id,
        "status": "updated",
        "response": response_data
    }