from pydantic import BaseModel
from typing import Optional


class LeadCreate(BaseModel):
    lead_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_source: Optional[str] = None
    lead_status: Optional[str] = None