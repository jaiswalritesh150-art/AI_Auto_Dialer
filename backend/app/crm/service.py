from datetime import datetime


def update_lead_after_call(
    zoho_lead_id: str,
    outcome: str,
    sentiment: str,
    summary: str
):
    if not zoho_lead_id:
        return {
            "success": False,
            "message": "Zoho Lead ID is required"
        }

    return {
        "success": True,
        "provider": "simulated_zoho",
        "zoho_lead_id": zoho_lead_id,
        "updated_fields": {
            "call_outcome": outcome,
            "call_sentiment": sentiment,
            "call_summary": summary,
            "last_called_at": datetime.utcnow()
        },
        "status": "updated"
    }