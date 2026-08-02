# Failed Attempt — Two Real Runtime Failures

This documents two genuine failures hit while running the app locally, exactly
as they happened, before being fixed (see `fixed_version.md`).

---

## Failure 1: Qdrant upload dropped mid-run

**Command run:**
```
python ingest.py
```

**What happened:** The script successfully cloned the transcripts repo (394
files, 25,164 chunks) and started uploading to Qdrant Cloud. It got to
4,000/25,164 chunks indexed, then crashed:

```
httpcore.ConnectError: [Errno 11001] getaddrinfo failed
...
qdrant_client.http.exceptions.UnexpectedResponse: Unexpected Response: 409 (Conflict)
Raw response content:
b'{"status":{"error":"Wrong input: Collection `lennys_transcripts` already exists!"},"time":0.023705548}'
```

**Root cause:** `getaddrinfo failed` is a DNS/network-level connection drop
(Windows error 11001) — a transient internet hiccup mid-upload, not a bug in
the ingestion logic. The follow-on 409 error was just a side effect of
re-running into a collection that was left half-populated by the interrupted
run.

---

## Failure 2: Anthropic SDK crashing on every chat request

**What happened:** After the ingestion issue was resolved and the backend
was started (`uvicorn app.main:app --reload --port 8000`), every chat message
from the frontend returned "Failed to fetch," and the backend logs showed:

```
TypeError: Client.__init__() got an unexpected keyword argument 'proxies'
```

Full trace pointed to `anthropic.Anthropic(api_key=...)` inside `llm.py`
failing during client construction.

**Root cause:** `requirements.txt` pinned `anthropic==0.34.2`, but `pip`
resolved a newer `httpx` version than that pinned SDK version was built
against. The newer `httpx` dropped a `proxies` kwarg that the older
`anthropic` package still passed internally — a dependency version mismatch,
not a logic bug. Because the crash happened server-side before any response
was sent, the browser only ever saw a dead connection, hence the generic
"Failed to fetch" on the frontend with no useful detail.

---

## Failure 3 (related): Anthropic billing blocked, Ollama not set up

Once the SDK crash was fixed, a new (expected, not a code bug) error
surfaced:

```
Anthropic API error: Error code: 400 - {'type': 'error', 'error':
{'type': 'invalid_request_error', 'message': 'Your credit balance is too
low to access the Anthropic API...'}}
```

and, when switching the UI toggle to the local provider:

```
Ollama error: 404 Client Error: Not Found for url: http://localhost:11434/api/chat
```

**Root cause:** No billing credit on the Anthropic account, and Ollama either
not running or the model not yet pulled. Both are account/environment setup
issues, not application bugs — which is also why the fix was to switch cloud
providers entirely rather than debug further (see `fixed_version.md`).
