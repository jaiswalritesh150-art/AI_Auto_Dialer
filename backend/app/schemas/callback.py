from datetime import datetime

from pydantic import BaseModel


class CallbackRequest(BaseModel):
    callback_at: datetime