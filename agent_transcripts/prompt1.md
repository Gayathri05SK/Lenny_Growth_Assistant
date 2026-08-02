# Prompt 1 — Initial Build Request

**Agent used:** Claude (claude.ai)
**Goal:** Scaffold the full-stack app from the assignment brief.

## Prompt given to the agent

>Explain the task given and what are the requirements i need to complete and how can i proceed to complete this task in an efficient way possible.
> give me tools suitable for this task and suggest tools like quadrant or any other tools which are mentioned in that task.
>Give me a code with simplest execution for this task and to complete this task
> [attached: assignment brief for "The Lenny Growth Assistant" — full-stack
> conversational app over Lenny's Podcast transcripts, FastAPI backend,
> Postgres persistence, cloud + local LLM toggle, RAG Q&A skill,
> Ship30for30-style content generation skill, in-app Artifact Viewer]

## What the agent produced

- FastAPI backend with session management (`/api/sessions`, `/api/chat`)
- SQLAlchemy models for `chat_sessions` and `chat_messages`
- An LLM abstraction (`llm.py`) supporting both a cloud provider and Ollama,
  selected per-request
- A RAG layer: `ingest.py` clones the public transcripts repo
  (`ChatPRD/lennys-podcast-transcripts`), chunks the text, and indexes it in
  a local vector store; `rag.py` queries it at runtime
- A skill router (`skills.py`) that picks between a grounded Q&A skill and a
  Ship30for30 essay-generation skill based on keyword triggers
- Artifact extraction: the LLM is prompted to wrap standalone documents in
  `<artifact type="markdown|html" title="...">` tags, which the backend
  parses out and the frontend renders in a separate viewer panel
- A plain HTML/CSS/JS frontend with a sidebar for sessions,
  a chat pane, and a collapsible artifact viewer
- README.md, design.md, PRD.md, ARCHITECTURE.md, docker-compose.yml, and a
  `.env.example`

## Outcome
Working end-to-end skeleton delivered as a downloadable zip on the first pass.
No failures at this stage — the interesting failures came later, during actual
local setup (see `failed_attempt.md`).
