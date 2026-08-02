import re
from . import rag

SHIP30_TRIGGERS = [
    "ship30", "ship 30", "ship30for30", "essay format", "write an essay",
    "linkedin post", "twitter thread", "x thread", "write a post",
    "atomic essay", "growth essay",
]

CODE_TRIGGERS = [
    "code", "python", "javascript", "typescript", "html", "css",
    "calculator", "snippet", "function", "script", "ui", "component",
]

ARTIFACT_HINT = (
    "\n\nIf — and only if — the user is asking you to produce a standalone "
    "document, essay, guide, or UI snippet (rather than a short conversational "
    "answer), return exactly one artifact block and nothing else outside it. "
    "The entire deliverable must be inside the artifact wrapper.\n"
    '<artifact type="markdown" title="Short Title Here">\n'
    "...full content...\n"
    "</artifact>\n"
    'Use type="html" instead of "markdown" only if the user explicitly asked for '
    "an HTML/CSS component. Do not use the artifact tags for normal short replies. "
    "For a standalone essay or document, do not prepend commentary, headings, or "
    "markdown outside the artifact block."
)

QA_SYSTEM = """You are the Lenny Growth Assistant, a product-management and growth
expert. Answer the user's question STRICTLY using the CONTEXT below, which is pulled
from real Lenny's Podcast/Newsletter transcripts. If the context doesn't contain a
relevant answer, say so honestly instead of guessing. Cite the source episode name
inline in parentheses when you use a specific insight.

CONTEXT:
{context}
""" + ARTIFACT_HINT

CODE_SYSTEM = """You are a coding assistant. If the user asks for code, return the
full code solution in a single artifact wrapper. Use markdown for code snippets and
plain HTML/CSS snippets only when the user explicitly asked for a UI/component artifact.
Do not add any extra explanation outside the artifact block.

Return exactly one artifact wrapper in this format:
<artifact type="markdown" title="Short Title Here">
```python
# code here
```
</artifact>
"""

SHIP30_SYSTEM = """You are the Lenny Growth Assistant, writing in the "Ship 30 for 30"
atomic essay style. Ground the content in the CONTEXT below (real insights from Lenny's
Podcast transcripts) — don't invent facts that contradict it.

Ship 30 for 30 style rules:
- Punchy, scroll-stopping hook in the first 1-2 lines (a bold claim, question, or
  counter-intuitive statement).
- Short sentences and short paragraphs (1-3 lines each). Heavy use of line breaks.
- Skimmable structure: bold subheads, numbered or bulleted lists, occasional em-dashes.
- One core idea per essay, built around a simple framework (e.g. "3 reasons",
  "The X Method").
- Concrete, specific examples over abstract theory.
- Ends with a clear, memorable takeaway or one-line summary a reader could screenshot.
- Target length: ~1250 words unless the user asks for something shorter (e.g. a
  LinkedIn post or thread, which should be much shorter and punchier).

CONTEXT:
{context}
""" + ARTIFACT_HINT

ARTIFACT_RE = re.compile(
    r'<artifact\s+type="(?P<type>markdown|html)"\s+title="(?P<title>[^"]*)"\s*>'
    r"(?P<content>.*?)</artifact>",
    re.DOTALL,
)


def route_skill(message: str) -> str:
    lower = message.lower()
    if any(t in lower for t in SHIP30_TRIGGERS):
        return "ship30"
    if any(t in lower for t in CODE_TRIGGERS):
        return "code"
    return "qa"


def build_prompt(skill: str, message: str):
    if skill == "code":
        return CODE_SYSTEM, message
    chunks = rag.query_transcripts(message, k=5 if skill == "qa" else 3)
    context = rag.format_context(chunks)
    system = (SHIP30_SYSTEM if skill == "ship30" else QA_SYSTEM).format(context=context)
    return system, message


def extract_artifact(raw_reply: str):
    """Splits an LLM reply into (clean_reply_text, artifact_dict_or_None)."""
    match = ARTIFACT_RE.search(raw_reply)
    if match:
        artifact = {
            "type": match.group("type"),
            "title": match.group("title").strip() or "Untitled Artifact",
            "content": match.group("content").strip(),
        }
        clean = (raw_reply[: match.start()] + raw_reply[match.end() :]).strip()
        if not clean:
            clean = f"Here's your {artifact['type']} artifact — **{artifact['title']}** (see the viewer panel)."
        return clean, artifact

    code_fence = re.search(r"```(?:\w+)?\s*(.*?)```", raw_reply, re.DOTALL)
    if code_fence:
        artifact = {
            "type": "markdown",
            "title": "Code Snippet",
            "content": code_fence.group(1).strip(),
        }
        clean = raw_reply[: code_fence.start()].strip()
        if not clean:
            clean = f"Here's your markdown artifact — **Code Snippet** (see the viewer panel)."
        return clean, artifact

    return raw_reply.strip(), None
