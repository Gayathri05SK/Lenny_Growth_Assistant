from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import desc

from . import models, schemas, skills
from .database import engine, get_db, Base
from .llm import get_llm_client, LLMError

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lenny Growth Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # simple local/demo setup; tighten for real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/sessions", response_model=schemas.SessionOut)
def create_session(db: DBSession = Depends(get_db)):
    session = models.ChatSession(title="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/api/sessions", response_model=list[schemas.SessionOut])
def list_sessions(db: DBSession = Depends(get_db)):
    return db.query(models.ChatSession).order_by(desc(models.ChatSession.created_at)).all()


@app.get("/api/sessions/{session_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(models.ChatSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(models.ChatSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}


@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat(req: schemas.ChatRequest, db: DBSession = Depends(get_db)):
    session = db.get(models.ChatSession, req.session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    provider = req.llm_provider or session.llm_provider
    if req.llm_provider and req.llm_provider != session.llm_provider:
        session.llm_provider = req.llm_provider  # remember the toggle per-session

    # Auto-title new chats from the first message
    if session.title == "New Chat":
        session.title = (req.message[:48] + "...") if len(req.message) > 48 else req.message

    db.add(models.ChatMessage(session_id=session.id, role="user", content=req.message))
    db.commit()

    skill = skills.route_skill(req.message)
    system_prompt, user_prompt = skills.build_prompt(skill, req.message)

    try:
        llm = get_llm_client(provider)
        raw_reply = llm.generate(system_prompt, user_prompt)
    except LLMError as e:
        raise HTTPException(502, str(e))

    clean_reply, artifact = skills.extract_artifact(raw_reply)
    if not artifact and skill == "ship30":
        artifact = {
            "type": "markdown",
            "title": "Ship30for30 Essay",
            "content": clean_reply,
        }

    msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=clean_reply,
        skill_used=skill,
        artifact_type=artifact["type"] if artifact else None,
        artifact_title=artifact["title"] if artifact else None,
        artifact_content=artifact["content"] if artifact else None,
    )
    db.add(msg)
    db.commit()

    return schemas.ChatResponse(
        reply=clean_reply,
        skill_used=skill,
        artifact=schemas.ArtifactOut(**artifact) if artifact else None,
    )
