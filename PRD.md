# PRD — Lenny Growth Assistant

## Problem
Product/growth practitioners have hundreds of hours of dense, high-signal insight
locked inside Lenny's Podcast transcripts, but no fast way to query it or turn it
into shareable content.

## Goal
A chat app that (1) answers grounded product/growth questions from the transcripts,
(2) can restyle those insights into a Ship30for30-style essay on demand, and (3)
renders any generated document/component in a dedicated viewer instead of a wall of
raw markdown in the chat log.

## Users
Single evaluator/demo user, running the app locally with their own API keys —
no multi-tenant or auth requirements for v1.

## User stories
1. As a user, I can start a new chat session and my previous sessions stay listed
   and re-openable, each with its own message history.
2. As a user, I can ask a product/growth question and get an answer grounded only
   in Lenny's transcripts, with the source episode referenced.
3. As a user, I can ask for that answer (or any topic) reformatted as a
   Ship30for30-style essay and get a ~1250-word, skimmable, bullet-heavy draft.
4. As a user, when the assistant produces a standalone document or HTML/CSS
   snippet, I see it rendered properly in a side panel, not as a code block I have
   to mentally parse, and I can copy the artifact payload directly from that panel.
5. As a user, I can switch between a cloud Groq model and a local Ollama model per
   message, without restarting the app or losing context.
6. As an evaluator, I can clone the repo, set two or three env vars, and have the
   whole thing running locally within a few minutes.

## Out of scope (v1)
- Multi-user auth
- Token-level streaming
- Mobile-responsive layout
- Editing/regenerating a past message

## Success metrics (for this take-home)
- Q&A skill answers are traceable to a specific transcript chunk.
- Ship30for30 skill output matches the style checklist (hook, brevity, bullets,
  bold subheads, single clear takeaway, ~1250 words).
- Artifact viewer correctly renders both markdown and HTML artifact types and
  exposes a copy affordance for reusable snippets.
- Provider toggle works with zero code changes, purely via `.env` / UI dropdown.
- Clean failure messages for the three likeliest failure modes: missing API key,
  Ollama not running, DB unreachable.

## Build approach
Built iteratively with an AI coding agent (see `agent_transcripts/`): schema and
API contract first, then LLM abstraction, then RAG ingestion, then skill routing,
then the frontend last once the API surface was stable — so the UI was built
against a real, working backend rather than mocked data.
