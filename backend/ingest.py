"""
One-time (or re-run whenever the transcript source updates) script that:
  1. Clones/pulls https://github.com/ChatPRD/lennys-podcast-transcripts
  2. Chunks every transcript file
  3. Embeds + stores the chunks in Qdrant (cloud or local)

Usage:
    cd backend
    python ingest.py
"""
import os
import subprocess
import sys

from qdrant_client import QdrantClient
from app.config import settings

REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts"
DATA_DIR = "./data/transcripts"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
TEXT_EXTENSIONS = {".md", ".txt"}


def clone_or_update_repo():
    if os.path.isdir(os.path.join(DATA_DIR, ".git")):
        print("Transcripts repo already present, pulling latest...")
        subprocess.run(["git", "-C", DATA_DIR, "pull"], check=True)
    else:
        os.makedirs("./data", exist_ok=True)
        print(f"Cloning {REPO_URL} ...")
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, DATA_DIR], check=True)


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def collect_files():
    files = []
    for root, _dirs, filenames in os.walk(DATA_DIR):
        if ".git" in root:
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in TEXT_EXTENSIONS:
                files.append(os.path.join(root, fn))
    return files


def main():
    try:
        clone_or_update_repo()
    except Exception as e:
        print(f"WARNING: could not clone repo ({e}). If you already have transcripts "
              f"in {DATA_DIR}, ingestion will continue with those.")

    files = collect_files()
    if not files:
        print(f"No .md/.txt transcript files found under {DATA_DIR}. Nothing to index.")
        sys.exit(1)

    print(f"Found {len(files)} transcript files. Building index...")

    if settings.qdrant_url:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        print(f"Connected to remote Qdrant at {settings.qdrant_url}")
    else:
        client = QdrantClient(path=settings.qdrant_local_path)
        print(f"Using local on-disk Qdrant at {settings.qdrant_local_path}")

    # Fresh collection each run to avoid duplicate chunks
    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)

    ids, docs, metas = [], [], []
    idx = 0
    for path in files:
        source_name = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for chunk in chunk_text(text):
            ids.append(idx)
            docs.append(chunk)
            metas.append({"source": source_name})
            idx += 1

    # client.add() auto-embeds each chunk with FastEmbed (default model:
    # BAAI/bge-small-en-v1.5, runs on CPU, no API key needed) and creates
    # the collection with the right vector size on first use.
    import time

    BATCH = 200
    for i in range(0, len(ids), BATCH):
        for attempt in range(1, 4):
            try:
                client.add(
                    collection_name=settings.qdrant_collection,
                    documents=docs[i : i + BATCH],
                    metadata=metas[i : i + BATCH],
                    ids=ids[i : i + BATCH],
                )
                break
            except Exception as e:
                if attempt == 3:
                    raise
                wait = attempt * 5
                print(f"  batch failed ({e}); retrying in {wait}s (attempt {attempt}/3)...")
                time.sleep(wait)
        print(f"  indexed {min(i + BATCH, len(ids))}/{len(ids)} chunks")