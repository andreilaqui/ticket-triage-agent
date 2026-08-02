# Ticket Triage & Knowledge Assistant

An agentic support-ticket triage system built with the Claude API. Given an
incoming support ticket, the agent searches a knowledge base, decides whether
it can confidently resolve the issue, and either drafts a cited reply or
escalates with a clear reason.

Built as a portfolio project modeled on real tourism/hospitality-ops support
workflows: classify → retrieve → resolve or escalate.

## Status
🚧 Work in progress — architecture and build log below.

## Scope (MoSCoW)

**Must have**
- BM25 search over the knowledge base
- Agentic tool-calling loop (search_kb → draft_reply / escalate)
- Core knowledge base docs covering Northstar's main business lines
- Sample ticket set covering happy-path, ambiguous, and out-of-scope cases
- CLI runner showing it end-to-end

**Should have**
- FastAPI wrapper exposing the same agent as `POST /tickets`, sharing one
  core function with the CLI (separation of concerns — the agent logic
  shouldn't know or care how it was invoked)
- A deliberate prompt-injection test ticket + documented handling
- Escalation reasoning shown in output, not just a black-box flag
- Basic test for the search module
- This README, documenting decisions and trade-offs as they're made

**Could have**
- Admin interface so non-technical staff can maintain KB content directly
  (no engineer required to update a price or policy)
- Embeddings/semantic search as an upgrade path over BM25
- Small web UI instead of CLI
- Model tiering (Haiku for triage, Sonnet for complex replies)

**Won't have**
- Real production ticket volume/infra — the 300-500/week figure is client
  flavor, not a target this repo is built to handle
- Real integration with an actual booking/PMS system
- Live weather/wildfire data feed — KB docs stay static, edited by hand
- Multi-tenant/auth system

## Architecture
_TODO: fill in once the agent loop is built._

## Setup
_TODO_

## Design decisions

**Search: BM25 (keyword), not embeddings.** Deterministic and debuggable —
every retrieval result traces back to actual shared vocabulary between the
ticket and a doc, no black-box similarity score. Known limitation: it only
catches word overlap. A ticket saying "I want my money back" won't match
`refund-cancellation-policy.md` unless it shares vocabulary with it. That's
an accepted trade-off for a demo where the KB and tickets are both
hand-written; embeddings are the documented upgrade path (see Could have).

**Decision logic: agentic tool-calling loop, not single structured output.**
Claude gets `search_kb`, `draft_reply`, and `escalate` as tools and decides
the sequence itself, rather than one prompt returning a JSON verdict. This
is the actual "agent" skill (judgment over a sequence of steps), not just
classification with extra formatting.

**Knowledge base freshness: files are re-read on every search, not cached
in memory.** At 8 small markdown files there's no performance cost to this,
and it avoids a real bug class (serving stale content after an update
because an in-memory copy wasn't invalidated). Would need revisiting at
real scale, but is free correctness here.

**KB maintenance: markdown files edited directly, for this demo only.** In
a real deployment, non-technical client staff would need to update prices
and policies without touching git or markdown syntax — that's the CMS/admin
interface noted under Could have.
