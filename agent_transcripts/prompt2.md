# Prompt 2 — Swapping in Supabase + Qdrant

**Agent used:** Claude (claude.ai)
**Goal:** Replace the initial local SQLite + Chroma setup with Supabase
(Postgres) and Qdrant (vector DB), per the assignment's suggested tooling.

## Prompt given to the agent

> i will use supabase and quadrant for quilk working of ingestion in vector db
> and complete ths task guide me

## What the agent changed

- `backend/requirements.txt`: removed `chromadb`, added
  `qdrant-client[fastembed]`
- `backend/app/config.py`: replaced Chroma settings (`chroma_dir`,
  `chroma_collection`) with Qdrant settings (`qdrant_url`, `qdrant_api_key`,
  `qdrant_local_path`, `qdrant_collection`) — supports either a hosted Qdrant
  Cloud cluster or a local on-disk fallback with no code change, just env vars
- `backend/app/rag.py`: rewritten to use `QdrantClient.query()` with Qdrant's
  built-in FastEmbed integration, so embeddings are generated automatically
  (no separate embeddings API/key needed)
- `backend/ingest.py`: rewritten to use `QdrantClient.add()` for indexing,
  same FastEmbed auto-embedding, batched in groups of 200 chunks
- `backend/.env.example`: updated to a Supabase pooler connection string
  format for `DATABASE_URL`, and the new `QDRANT_*` variables
- `docker-compose.yml`: added an optional local Qdrant service alongside the
  optional local Postgres, for anyone who doesn't want to use the cloud
  free tiers
- README.md / ARCHITECTURE.md: rewritten sections to document the Supabase +
  Qdrant setup step by step (where to find the connection string, pooler vs
  direct connection, Qdrant Cloud cluster creation, etc.)

## Validation done by the agent before handing back the code
- Ran `python -m py_compile` on every changed file to catch syntax errors
- Installed `qdrant-client[fastembed]` in a scratch virtual environment to
  confirm the dependency actually resolves and imports cleanly
- Ran a live smoke test of `client.add()` / `client.query()` against a local
  on-disk Qdrant instance with a small fake transcript, to verify the
  response object shape (`.document`, `.metadata`, `.score`) matched what the
  new `rag.py` code expected, before shipping it

## Outcome
Updated zip delivered; user then ran `ingest.py` against their real Supabase
+ Qdrant Cloud accounts. That real run is where the first genuine failure
happened — see `failed_attempt.md`.
