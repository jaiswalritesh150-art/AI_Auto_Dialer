from pydantic import BaseModel
from typing import Optional


class CallResultRequest(BaseModel):
    queue_id: int
    attempt_id: int
    status: str
    result: Optional[str] = None
    failure_reason: Optional[str] = None