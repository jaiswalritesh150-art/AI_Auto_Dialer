import re


def validate_phone(phone: str):
    """
    Validate and normalize a phone number.
    """

    if not phone:
        return {
            "valid": False,
            "phone": None,
            "message": "Phone number is required"
        }

    cleaned_phone = re.sub(r"[^\d+]", "", phone)

    # Indian 10-digit number
    if re.fullmatch(r"[6-9]\d{9}", cleaned_phone):

        normalized_phone = "+91" + cleaned_phone

        return {
            "valid": True,
            "phone": normalized_phone,
            "message": "Valid Indian phone number"
        }

    # International number
    if re.fullmatch(r"\+[1-9]\d{9,14}", cleaned_phone):

        return {
            "valid": True,
            "phone": cleaned_phone,
            "message": "Valid international phone number"
        }

    return {
        "valid": False,
        "phone": None,
        "message": "Invalid phone number"
    }