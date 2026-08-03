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
interface noted under Could have. AI assistance for drafting content is a
reasonable enhancement to that interface later, but a human owning and
approving what gets published is the assumed default, not a fully
autonomous AI-maintained knowledge base.

## Known limitations (found through testing, not assumed)

**Cross-document retrieval precision is imperfect.** Testing found that
cross-reference disclaimers written for human readers — e.g. the hotel
refund doc's note "vacation rentals have a separate policy, see
vacation-rental-policies.md" — leak the referenced doc's distinctive
vocabulary ("vacation," "rental," "tours") into the source doc. Confirmed
by word-frequency analysis, not just by eyeballing scores. Net effect: for
some queries (e.g. one mentioning "wildfire" + "tour"), BM25 ranks the
*wrong* doc first, because the hotel refund doc's own disclaimer happens
to contain the word "tour."

**Deliberately not fixed yet, and here's the reasoning why:** search
returns the top 3 candidates, not just the top 1, and the correct doc
still appears in that shortlist in every case tested. The actual
disambiguation is deferred to the agent, which reads full document
content, not just a ranking score. Fixing search precision in isolation
— before confirming whether it actually causes a wrong final answer —
risks optimizing a layer that may not matter. Revisit if the *agent's
final answers* turn out wrong, not just if a ranking score looks
imperfect in isolation.

**Why this matters more, not less, in production:** this project's 8
docs are unusually clean — written once, by one person (me), all at once.
Real knowledge base content is maintained over time by multiple
non-technical staff, none of whom have a reason to think about keyword
overlap when writing a helpful cross-reference note — nor should they
have to. That means this exact failure mode gets *more* likely over time
in a real deployment, not less. It's a real argument for treating the
agent's own reasoning as the primary safety net against imperfect
retrieval, rather than depending on search to stay precise — since
production content will always be messier than a demo corpus written in
one sitting.
