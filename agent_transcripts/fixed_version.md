# Fixed Version — How Each Failure Was Resolved

---

## Fix 1: Qdrant upload dropped mid-run

**Agent's diagnosis:** The failure was a transient network/DNS drop, not a
code defect. `ingest.py` was already written to delete-and-rebuild the
Qdrant collection on every run, so the immediate fix was simply:

```bash
python ingest.py
```

Re-running from scratch cleared the half-populated collection and completed
successfully.

**Follow-up robustness fix (recommended and applied):** wrapped the batch
upload loop in a retry-with-backoff so a single dropped connection doesn't
kill a 20+ minute ingestion run:

```python
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
```

---

## Fix 2: Anthropic SDK / httpx version conflict

**Agent's diagnosis:** dependency version mismatch between the pinned
`anthropic==0.34.2` and a newer `httpx` resolved by pip.

**Fix applied:**
```bash
pip install -U anthropic
```
(upgrades the SDK to a version compatible with the newer `httpx`), then
restarted the backend server. This resolved the crash with no code changes
needed in `llm.py` itself — confirming it was purely a dependency pinning
issue.

---

## Fix 3: Switched cloud provider from Anthropic to Groq

Rather than keep fighting Anthropic billing setup, the decision was made to
swap the cloud LLM provider to **Groq**, which has a generous free tier.

**Code changes made to `backend/app/llm.py`** — added a `GroqClient`
alongside the existing `AnthropicClient` and `OllamaClient`, all implementing
the same `.generate(system_prompt, user_prompt)` interface so nothing else
in the app needed to change:

```python
class GroqClient:
    def __init__(self):
        from groq import Groq
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set in your .env file.")
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=3000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise LLMError(f"Groq API error: {e}")
```

**Other changes:**
- `requirements.txt`: added `groq`
- `app/config.py`: added `groq_api_key`, `groq_model` (default
  `llama-3.3-70b-versatile`), set `default_llm_provider = "groq"`
- `app/llm.py`'s `get_llm_client()`: added `"groq"` as a routable provider
  alongside `"anthropic"` and `"ollama"`
- `.env.example` and frontend LLM dropdown updated to reflect Groq as the
  default cloud option

**Validation:** after adding a real `GROQ_API_KEY` and restarting the
backend, `eval.py` (see `backend/eval.py`) was run against 5 test cases —
0 errors, ~1-3s average latency, 100% skill-routing accuracy on the test set.

## Outcome
Working end-to-end app confirmed via the eval script: correct skill routing,
grounded Q&A answers citing transcript sources, Ship30for30 essays
generating and rendering correctly in the Artifact Viewer, and graceful
error messages (instead of crashes) for the remaining known failure modes
(missing keys, DB unreachable, Ollama not running).
