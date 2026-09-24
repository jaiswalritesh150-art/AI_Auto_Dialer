from pydantic import BaseModel


class CallIntelligenceRequest(BaseModel):
    queue_id: int
    attempt_id: int
    transcript: str
    
class AIConversationRequest(BaseModel):
    message: str
    conversation: list[dict] = []