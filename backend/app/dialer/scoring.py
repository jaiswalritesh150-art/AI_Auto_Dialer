def calculate_lead_score(lead):
    """
    Calculate a simple rule-based score for a lead.

    Maximum score: 100
    """

    score = 0

    # Phone number available
    if lead.phone:
        score += 30

    # Email available
    if lead.email:
        score += 20

    # Company available
    if lead.company:
        score += 20

    # Lead came from website
    if lead.lead_source:
        if lead.lead_source.lower() == "website":
            score += 15

    # New lead
    if lead.lead_status:
        if lead.lead_status.lower() == "new":
            score += 15

    # Determine priority
    if score >= 80:
        priority = "HIGH"
    elif score >= 50:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return score, priority
