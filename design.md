# Design Notes — UI/UX

## Layout philosophy
Three-column layout modeled on familiar chat products (ChatGPT/Claude), so the
evaluator has zero learning curve:

1. **Sidebar (sessions)** — persistent list of chats, newest first, with a single
   prominent "+ New Chat" action. Each session auto-titles itself from the first
   user message so the list stays scannable.
2. **Chat pane (center)** — the primary focus. User and assistant bubbles are
   visually distinct (right-aligned/indigo for user, left-aligned/neutral for
   assistant). Assistant replies carry a small skill tag ("Q&A skill" vs
   "Ship30for30 skill") so the routing logic is transparent to the user, not a
   black box.
3. **Artifact panel (right, collapsible)** — only appears when a message contains
   an artifact, mirroring how modern AI assistants expose shared deliverables.
   It stays hidden until something is worth showing, then opens automatically and
   can be dismissed with ✕. Markdown artifacts render through `marked.js`; HTML
   artifacts render inside a sandboxed `<iframe srcdoc>` so arbitrary generated
   HTML/CSS can't break the host page. A **Copy** button sits in the panel header
   so code snippets and standalone markdown artifacts can be reused directly.

## Interaction principles
- **Low friction over cleverness.** Enter sends the message (Shift+Enter for a
  newline) — no hidden gestures.
- **Visible system state.** The LLM toggle (Cloud vs Local) lives in the header at
  all times, not buried in a settings modal, because switching engines mid-task is
  a core requirement of the assignment, not an edge case.
- **Graceful failure.** Backend errors (missing API key, Ollama not running, DB
  down) surface as a plain-language message directly in the chat thread rather than
  a silent failure or raw stack trace, so a non-technical evaluator can self-diagnose.
- **Skill transparency.** Because the assignment is evaluated partly on "how the
  agent decides which skill to use," the UI intentionally exposes that decision
  (skill tag per message) instead of hiding it — good for grading, good for user
  trust.

## Visual language
Dark theme, single accent color (indigo/violet) used sparingly for primary actions
(New Chat button, Send button, artifact chip) so it reads as intentional rather than
decorative. Typography relies on the system font stack for fast load and native
feel — no external font requests needed beyond `marked.js`.

## Deliberate scope cuts (documented, not hidden)
- No streaming token-by-token rendering — the whole reply arrives at once. This
  keeps the FastAPI layer simple (regular JSON response instead of SSE) and was
  judged not worth the added complexity for a take-home timeline. A "Thinking..."
  placeholder bubble covers the wait.
- No auth/multi-user accounts — sessions are anonymous, matching the assignment's
  scope (single evaluator running it locally).
- No drag-resize on the artifact panel — fixed width keeps the CSS simple; would be
  a natural next iteration.
