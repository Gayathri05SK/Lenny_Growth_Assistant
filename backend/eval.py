"""
Simple eval script for the Lenny Growth Assistant.

Checks:
  1. LATENCY        - how long each /api/chat call takes
  2. SKILL ROUTING   - did it pick "qa" vs "ship30" correctly?
  3. RELEVANCY       - does the reply mention expected keywords? (simple, no extra LLM call needed)
  4. GROUNDING       - for "unknown" questions, does it admit it doesn't know instead of making things up?
  5. ARTIFACT CHECK  - for essay requests, did it actually produce an artifact?

Usage:
    cd backend
    python eval.py

Make sure your backend is running first:  uvicorn app.main:app --port 8000
"""

import time
import csv
import requests

API_BASE = "http://localhost:8000/api"

# ---- 1. Define your test cases here ----
# expected_skill: "qa" or "ship30"
# expect_keywords: list of words/phrases that SHOULD appear in a good answer (relevancy check)
# expect_artifact: True if this should trigger the Artifact Viewer
# is_unknown_check: True if this question is NOT covered by the transcripts (grounding check)
TEST_CASES = [
    {
        "message": "What do the transcripts say about product-market fit?",
        "expected_skill": "qa",
        "expect_keywords": ["product", "market", "fit"],
        "expect_artifact": False,
        "is_unknown_check": False,
    },
    {
        "message": "What are growth loops and how do they work?",
        "expected_skill": "qa",
        "expect_keywords": ["growth", "loop"],
        "expect_artifact": False,
        "is_unknown_check": False,
    },
    {
        "message": "Write this as a Ship30for30 essay about onboarding.",
        "expected_skill": "ship30",
        "expect_keywords": ["onboarding"],
        "expect_artifact": True,
        "is_unknown_check": False,
    },
    {
        "message": "Write a LinkedIn post about retention strategies.",
        "expected_skill": "ship30",
        "expect_keywords": ["retention"],
        "expect_artifact": True,
        "is_unknown_check": False,
    },
    {
        "message": "What is the recipe for my grandmother's apple pie?",
        "expected_skill": "qa",
        "expect_keywords": [],
        "expect_artifact": False,
        "is_unknown_check": True,  # not in transcripts -> should say "don't know", not hallucinate
    },
]


def create_session():
    resp = requests.post(f"{API_BASE}/sessions")
    resp.raise_for_status()
    return resp.json()["id"]


def run_case(session_id, case):
    start = time.time()
    error = None
    reply = ""
    skill_used = None
    has_artifact = False

    try:
        resp = requests.post(
            f"{API_BASE}/chat",
            json={"session_id": session_id, "message": case["message"]},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("reply", "")
        skill_used = data.get("skill_used")
        has_artifact = data.get("artifact") is not None
    except Exception as e:
        error = str(e)

    latency = round(time.time() - start, 2)

    # --- checks ---
    skill_correct = (skill_used == case["expected_skill"]) if not error else False

    reply_lower = reply.lower()
    keywords_found = [kw for kw in case["expect_keywords"] if kw.lower() in reply_lower]
    relevancy_score = (
        round(len(keywords_found) / len(case["expect_keywords"]), 2)
        if case["expect_keywords"] else None
    )

    artifact_correct = (has_artifact == case["expect_artifact"]) if not error else False

    grounding_ok = None
    if case["is_unknown_check"] and not error:
        # crude check: reply should contain an "I don't know" style phrase
        admits_unknown = any(
            phrase in reply_lower
            for phrase in ["don't know", "do not know", "no information",
                            "not covered", "doesn't contain", "not mentioned",
                            "couldn't find", "could not find", "unable to find"]
        )
        grounding_ok = admits_unknown

    return {
        "message": case["message"],
        "error": error or "",
        "latency_sec": latency,
        "expected_skill": case["expected_skill"],
        "actual_skill": skill_used or "",
        "skill_correct": skill_correct,
        "relevancy_score": relevancy_score,
        "keywords_found": ", ".join(keywords_found),
        "expect_artifact": case["expect_artifact"],
        "has_artifact": has_artifact,
        "artifact_correct": artifact_correct,
        "grounding_ok": grounding_ok,
        "reply_preview": (reply[:120] + "...") if len(reply) > 120 else reply,
    }


def main():
    print(f"Running {len(TEST_CASES)} eval cases against {API_BASE} ...\n")
    session_id = create_session()

    results = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {case['message'][:60]}...")
        result = run_case(session_id, case)
        results.append(result)
        status = "OK" if not result["error"] else f"ERROR: {result['error']}"
        print(f"    latency={result['latency_sec']}s  skill={result['actual_skill']}  {status}\n")

    # --- write CSV ---
    with open("eval_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    # --- summary ---
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    avg_latency = round(sum(r["latency_sec"] for r in results) / total, 2)
    skill_acc = round(sum(1 for r in results if r["skill_correct"]) / total * 100, 1)
    relevancy_scores = [r["relevancy_score"] for r in results if r["relevancy_score"] is not None]
    avg_relevancy = round(sum(relevancy_scores) / len(relevancy_scores) * 100, 1) if relevancy_scores else None
    artifact_acc = round(sum(1 for r in results if r["artifact_correct"]) / total * 100, 1)
    grounding_checks = [r["grounding_ok"] for r in results if r["grounding_ok"] is not None]
    grounding_acc = (
        round(sum(1 for g in grounding_checks if g) / len(grounding_checks) * 100, 1)
        if grounding_checks else None
    )

    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total test cases:     {total}")
    print(f"Errors/crashes:       {errors}")
    print(f"Avg latency:          {avg_latency}s")
    print(f"Skill routing acc:    {skill_acc}%")
    print(f"Avg relevancy score:  {avg_relevancy}%" if avg_relevancy is not None else "Avg relevancy score:  n/a")
    print(f"Artifact accuracy:    {artifact_acc}%")
    print(f"Grounding accuracy:   {grounding_acc}%" if grounding_acc is not None else "Grounding accuracy:   n/a (no unknown-question tests)")
    print("\nFull details saved to eval_results.csv")


if __name__ == "__main__":
    main()