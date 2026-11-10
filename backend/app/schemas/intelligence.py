
from pydantic import BaseModel, Field


class CallIntelligenceRequest(BaseModel):
    queue_id: int
    attempt_id: int
    transcript: str


class AIConversationRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Latest message received from the lead"
    )

    conversation: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
