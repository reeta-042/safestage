from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatRequest(BaseModel):
    event_id: str
    message: str = Field(..., min_length=1)
    history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    event_id: str
    reply: str
    context_used: Dict[str, Any]
