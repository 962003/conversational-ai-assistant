"""Pydantic request/response models."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message text")
    session_id: str = Field("web-session", description="Conversation/session id")


class Source(BaseModel):
    doc: str
    title: str
    score: float
    method: str | None = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    kb_hit: bool
    escalated: bool = False
    sentiment: str | None = None
    confidence: float = 0.0
    confidence_label: str = "low"
    sources: list[Source] = []
    session_id: str
    via: str = "direct"  # "direct" or "dialogflow-cx"


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class TicketRequest(BaseModel):
    session_id: str = "web-session"
    name: str
    email: str
    issue: str
