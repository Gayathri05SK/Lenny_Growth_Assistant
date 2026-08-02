# Lenny Growth Assistant

A conversational, RAG-powered web app over *Lenny's Podcast* transcripts, with a
Ship30for30-style content skill and an in-app Artifact Viewer — built with FastAPI,
Qdrant, Supabase (Postgres), and a plain HTML/JS frontend (no build step required).

## 1. Architecture overview

```
┌──────────────┐    fetch()     ┌────────────────────┐        ┌──────────────┐
│  Frontend    │ ─────────────▶ |   FastAPI backend   │ ─────▶ │  LLM Toggle   │
│ (index.html, │ ◀───────────── │   app/main.py        │        │  Groq API     │
│  app.js)     │                │                      │        │      or       │
└──────────────┘                │  1. save user msg    │        │  Ollama (local)│
                                 │  2. route_skill()    │        └──────────────┘
                                 │  3. RAG retrieval ───┼──────▶ Qdrant (cloud or
                                 │  4. call LLM          │        local vector store,
                                 │  5. extract artifact  │        built by ingest.py
                                 │  6. save + return     │        from the transcripts
                                 └──────────┬───────────┘        repo)
                                            │
                                            ▼
                                 Postgres / SQLite
                                 (chat_sessions, chat_messages)
```

- **Frontend**: static HTML/CSS/JS. Sidebar = sessions ("New Chat" button spins up a
  fresh session, exactly like ChatGPT). Center = chat. Right panel = **Artifact
  Viewer**, which renders Markdown (via marked.js) or sandboxed HTML (via `<iframe
  srcdoc>`) inline, side-by-side with the conversation.
- **Backend (`backend/app/`)**:
  - `main.py` — FastAPI routes for sessions + chat.
  - `skills.py` — the "agentic routing" layer. `route_skill()` inspects the message
    and picks the **Q&A skill** (RAG-grounded product/growth answers), the
    **Ship30for30 skill** (long-form essay generation in that style), or the
    **Code skill** for calculator/snippet-style deliverables. The code skill is
    returned as a markdown artifact so it can be copied directly from the side
    viewer.
  - `rag.py` — queries a **Qdrant** collection (cloud or local) for relevant
    transcript chunks, embedding on the fly via Qdrant's built-in FastEmbed.
  - `llm.py` — the **LLM toggle**: one interface, two implementations
    (`GROQClient`, `OllamaClient`), selected per-request from the UI dropdown.
  - `models.py` / `database.py` — SQLAlchemy models + engine, pointed at Postgres
    (Supabase/Railway) or SQLite via a single `DATABASE_URL` env var.
- **Artifacts**: the LLM is instructed (via prompt) to wrap standalone deliverables
  in `<artifact type="markdown|html" title="...">...</artifact>`. The backend
  extracts that block with a regex (`skills.extract_artifact`), stores it separately
  in the DB, and returns it to the frontend for rendering in the viewer panel. The
  viewer now also exposes a **Copy** action for the active artifact payload.

## 2. Tools you need (install/create before running)

| Tool | Why | Get it |
|---|---|---|
| Python 3.10+ | backend | https://python.org |
| Git | clone transcripts repo | usually preinstalled |
| A **Supabase** project | Postgres persistence | https://supabase.com (free tier) |
| A **Qdrant Cloud** cluster (or local Qdrant, see below) | vector DB for RAG | https://cloud.qdrant.io (free tier) |
| A **Groq** API key **or** Ollama installed locally | the two LLM options | https://console.groq.com (cloud) / https://ollama.com (local) |

You do **not** need Node.js — the frontend is plain HTML/JS served as static files.

## 3. Step-by-step: Supabase (Postgres)

1. Go to https://supabase.com → New Project → pick a name, region, and a DB
   password (save it, you'll need it below).
2. Once the project is ready: **Project Settings → Database → Connection string**.
3. Select the **"Transaction pooler"** tab (port `6543`) — this works from any
   network without IP allow-listing, which is what you want for local dev.
4. Copy it and paste into `backend/.env` as `DATABASE_URL`, swapping in your real
   password:
   ```
   DATABASE_URL=postgresql://postgres.xxxxxxxx:YOUR-PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
   ```
5. That's it — tables are created automatically on first run
   (`Base.metadata.create_all()` in `main.py`). No manual SQL needed.

## 4. Step-by-step: Qdrant

You have two options — pick whichever is easier for you:

**Option A — Qdrant Cloud (recommended, matches "quick working" best):**
1. Go to https://cloud.qdrant.io → sign up → Create Cluster (free tier, 1GB is
   plenty for this dataset).
2. Once it's up, copy the **Cluster URL** and generate an **API key**.
3. In `backend/.env`:
   ```
   QDRANT_URL=https://xxxxxxxx.us-east.aws.cloud.qdrant.io:6333
   QDRANT_API_KEY=your-qdrant-api-key
   ```

**Option B — local Qdrant, zero cloud setup:**
Just leave `QDRANT_URL` blank in `.env`. The app will use an embedded, file-backed
Qdrant instance at `./qdrant_data` — no server, no API key, nothing to sign up for.
(There's also a `docker compose up -d qdrant` option in `docker-compose.yml` if you
want a real local Qdrant server instead of the embedded mode.)

Embeddings are generated automatically via Qdrant's built-in **FastEmbed**
integration (a small local ONNX model, `BAAI/bge-small-en-v1.5`) — you don't need
a separate embeddings API key even when using Qdrant Cloud. The first run downloads
the model (~130MB) and caches it.

## 5. Full setup (Supabase + Qdrant Cloud + Groq)

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:
```
DATABASE_URL=postgresql://postgres.xxxxxxxx:YOUR-PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
QDRANT_URL=https://xxxxxxxx.us-east.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
DEFAULT_LLM_PROVIDER=GROQ
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2:0.5b
```

```bash
# Build the knowledge base (clones Lenny's transcripts repo, chunks it,
# embeds + uploads to Qdrant) — takes a few minutes the first time
python ingest.py

# Run the API
uvicorn app.main:app --reload --port 8000

# In another terminal, serve the frontend
cd ../frontend
python3 -m http.server 5500
```

Open `http://127.0.0.1:5500`, ask a product/growth question, and it'll retrieve
from Qdrant and answer via Groq. Toggle "Local (Ollama)" any time if you also
want to demo the local-LLM path (`ollama serve` + `ollama pull qwen2:0.5b` or
another small local model).

## 6. Environment variables (`backend/.env`, see `.env.example`)

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Supabase Postgres connection string (pooler, port 6543) |
| `DEFAULT_LLM_PROVIDER` | `GROQ` or `ollama` |
| `GROQ_API_KEY` / `GROQ_MODEL` | cloud LLM |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | local LLM |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud cluster (leave URL blank for local on-disk Qdrant) |
| `QDRANT_LOCAL_PATH` | where the embedded Qdrant stores data, if `QDRANT_URL` is blank |
| `QDRANT_COLLECTION` | name of the vector collection |

**Never commit your real `.env`** — only `.env.example` is checked in.

## 7. Re-indexing the knowledge base

Run `python ingest.py` again any time the transcripts repo updates. It deletes and
rebuilds the Qdrant collection each time, so it's always safe to re-run.
