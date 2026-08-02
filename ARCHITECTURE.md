# Architecture

## Database schema

**`chat_sessions`**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| title | string | auto-set from first user message |
| llm_provider | string | last-used provider for this session, "groq" or "ollama" |
| created_at | datetime | |

**`chat_messages`**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| session_id | string | FK -> chat_sessions.id |
| role | string | "user" \| "assistant" |
| content | text | the clean reply (artifact block stripped out) |
| skill_used | string, nullable | "qa" \| "ship30" \| "code", null for user messages |
| artifact_type | string, nullable | "markdown" \| "html" |
| artifact_title | string, nullable | |
| artifact_content | text, nullable | full artifact body |
| created_at | datetime | |

Managed via SQLAlchemy ORM (`backend/app/models.py`); works against Postgres
(Supabase/Railway) or SQLite (`DATABASE_URL` env var is the only difference).
`Base.metadata.create_all()` runs on startup, so no manual migration step is needed
for this scope.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness check |
| POST | `/api/sessions` | create a new chat session |
| GET | `/api/sessions` | list sessions, newest first |
| GET | `/api/sessions/{id}/messages` | full history for one session |
| DELETE | `/api/sessions/{id}` | delete a session + its messages (cascade) |
| POST | `/api/chat` | send a message, get a routed + grounded reply |

`POST /api/chat` request body: `{session_id, message, llm_provider?}`.
Response: `{reply, skill_used, artifact?: {type, title, content}}`.

## Agentic routing logic

1. `skills.route_skill(message)` — keyword match against a `SHIP30_TRIGGERS` list
   (e.g. "ship30", "write an essay", "linkedin post", "twitter thread") and a
   `CODE_TRIGGERS` list for calculator/code/snippet prompts. Match → `"ship30"`
   or `"code"`; otherwise → `"qa"` (the default, always-safe path).
2. `skills.build_prompt(skill, message)` — the Q&A and Ship30 paths call
   `rag.query_transcripts()` for grounding context, then format it into a
   skill-specific system prompt (`QA_SYSTEM` enforces strict grounding + honesty
   about gaps; `SHIP30_SYSTEM` encodes the style checklist: hook, brevity,
   bullets, bold subheads, one framework, concrete examples, clear takeaway,
   ~1250 words). The `code` path uses a code-focused system prompt that returns a
   single artifact-wrapped block so the artifact viewer can display and copy it.
3. Both system prompts append a shared `ARTIFACT_HINT` instructing the model to
   wrap standalone deliverables in `<artifact type="..." title="...">...</artifact>`.
4. `skills.extract_artifact(raw_reply)` regex-splits that block out of the reply
   before it's shown as a chat bubble, so the chat log stays skimmable and the full
   artifact goes to the viewer panel + DB. If the model omits the wrapper for a
   code/Ship30 answer, the backend falls back to a deterministic artifact payload
   using the reply body itself.

This keeps routing simple, inspectable, and free of an extra LLM call just to
classify intent — appropriate for the current set of clearly distinguishable
skills. A natural extension point (not implemented, out of scope) would be
swapping the keyword router for a small classifier call if more skills are added
later.

## LLM toggle implementation

`app/llm.py` exposes `get_llm_client(provider)`, returning either:
- `GROQClient` — wraps a `POST https://api.groq.com/openai/v1/chat/completions`
  call using the Groq OpenAI-compatible endpoint.
- `OllamaClient` — wraps a `POST {OLLAMA_HOST}/api/chat` call.

Both implement the same `.generate(system_prompt, user_prompt) -> str` interface,
so `main.py`'s chat handler doesn't know or care which one it's using. The provider
is resolved per-request: `req.llm_provider` (from the UI dropdown) overrides the
session's last-used provider, which overrides `DEFAULT_LLM_PROVIDER` from `.env`.
Connection/auth failures raise a typed `LLMError` that becomes a clean HTTP 502
with a human-readable message (missing key, Ollama not running, timeout, etc.)
instead of a raw traceback.

## RAG pipeline (Qdrant)

- `ingest.py` (run offline/on-demand): clones/pulls the transcripts repo, walks
  `.md`/`.txt` files, splits into ~1200-char overlapping chunks, and calls
  `QdrantClient.add(collection_name, documents=..., metadata=..., ids=...)`.
  This uses Qdrant's built-in **FastEmbed** integration to embed every chunk
  locally (default model `BAAI/bge-small-en-v1.5`, CPU-only ONNX, no external
  embeddings API) and upserts the vectors + `{"source": <episode filename>}`
  payload into the collection — creating it automatically on first use.
- `rag.py` (runtime): `query_transcripts(query, k)` calls
  `QdrantClient.query(collection_name, query_text=query, limit=k)`, which embeds
  the query with the same FastEmbed model and returns the top-k nearest chunks
  (each a `QueryResponse` with `.document`, `.metadata`, `.score`).
  `format_context()` turns those into the prompt's CONTEXT block.
- **Qdrant Cloud vs local**: `_get_client()` connects to `QDRANT_URL` (+
  `QDRANT_API_KEY`) if set, otherwise falls back to an embedded, file-backed
  Qdrant at `QDRANT_LOCAL_PATH` — same API either way, so switching between them
  is a config change, not a code change.

## Postgres (Supabase)

`DATABASE_URL` points at Supabase's connection pooler (port 6543), which is
network-friendly for local dev (no IP allow-listing required). SQLAlchemy handles
everything else identically to any other Postgres instance — `models.py` and
`database.py` have no Supabase-specific code, so swapping to Railway or a
self-hosted Postgres is a one-line env change.
