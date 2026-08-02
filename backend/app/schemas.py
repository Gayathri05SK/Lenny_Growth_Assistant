from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionOut(BaseModel):
    id: str
    title: str
    llm_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    skill_used: Optional[str] = None
    artifact_type: Optional[str] = None
    artifact_title: Optional[str] = None
    artifact_content: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: str
    message: str
    llm_provider: Optional[str] = None  # "groq" | "ollama", overrides session default


class ArtifactOut(BaseModel):
    type: str
    title: str
    content: str


class ChatResponse(BaseModel):
    reply: str
    skill_used: str
    artifact: Optional[ArtifactOut] = None
