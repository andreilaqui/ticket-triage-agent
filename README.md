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
- Knowledge base docs covering Northstar's main business lines
- Agentic tool-calling loop (Claude reads the full KB as context, then
  decides: `draft_reply` or `escalate`)
- Sample ticket set covering happy-path, ambiguous, and out-of-scope cases
- CLI runner showing it end-to-end
- BM25 search module, built and tested — but not on the live agent path,
  see "Retrieval architecture" below for why

**Should have**
- FastAPI wrapper exposing the same agent as `POST /tickets`, sharing one
  core function with the CLI (separation of concerns — the agent logic
  shouldn't know or care how it was invoked)
- A deliberate prompt-injection test ticket + documented handling
- Escalation reasoning shown in output, not just a black-box flag
- Basic tests for search and for KB cross-reference integrity
  (`check_references.py`)
- This README, documenting decisions and trade-offs as they're made

**Could have**
- Admin interface so non-technical staff can maintain KB content directly
  (no engineer required to update a price or policy)
- Re-enabling retrieval (BM25 or an embeddings upgrade) once the KB
  outgrows full-context inclusion — see "Scalability path" below
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

**Knowledge base delivery: full-context inclusion, not retrieval — at this
scale.** The entire knowledge base measures 1,600 words / ~2,200 tokens
across 8 docs (measured, not estimated). Small enough to include directly
in every prompt, which eliminates the ranking problem entirely — there's
no "wrong doc" to retrieve if Claude reads the complete text of all of
them every time. Made cost-effective by Claude's prompt caching, designed
for exactly this pattern: large, static, repeatedly-reused context. A full
BM25 module (`search.py`) was built and tested first; see "Retrieval
architecture" below for why it's not what powers the live agent, and
"Scalability path" for when that would change.

**Decision logic: agentic tool-calling loop, not single structured
output.** Claude gets `draft_reply` and `escalate` as tools and decides
which to call based on whether the full knowledge base — given directly
in context — actually contains enough to answer confidently. This is the
real "agent" skill (judgment over available information, including
knowing when *not* to answer), not classification with extra formatting.

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

## Retrieval architecture: built, tested, and deliberately not the live path

A full BM25 keyword-search module (`search.py`) was built first, against
all 8 knowledge base docs. Testing surfaced two genuine precision bugs
along the way — both confirmed through diagnostics, not assumed:

1. **Cross-reference leakage.** Disclaimer notes written for human readers
   (e.g. "vacation rentals have a separate policy, see X.md") leaked the
   referenced doc's vocabulary into the source doc — BM25 can't tell
   "mentions X to rule it out" from "mentions X because it's relevant."
   Fixed by moving cross-references into a `## See Also` section, stripped
   before indexing but still shown to the agent when it reads a doc.
2. **Topical dilution.** Even after that fix, a narrowly-scoped doc (the
   hotel refund policy — 100% about cancellation) structurally out-scores
   a broader multi-topic doc (vacation rental policies, where cancellation
   is one section among several) on cancellation-related queries. This is
   a known limitation of whole-document BM25 generally, not a bug specific
   to this implementation — chunking by section is the real fix, and was
   evaluated and deliberately not built (see below).

Both are documented precisely: `check_references.py` validates `## See
Also` links point to real files, and `tests/test_search.py` has
regression tests against the exact queries that first exposed each bug.

**Then the scale question got asked, and it changed the answer.** The
entire knowledge base measures 1,600 words / ~2,200 tokens, total, across
all 8 docs. Small enough to include directly in every prompt — which
eliminates the ranking problem completely, since there's no "wrong doc"
to retrieve if Claude reads the full, actual text of all of them every
time. This is made cost-effective by Claude's prompt caching, which is
designed for exactly this pattern: large, static, repeatedly-reused
context checked on every incoming ticket.

**So `search.py` stays in the repo, fully built and tested, but the live
agent uses full-context inclusion instead.** This isn't abandoning
precision — it's choosing the simpler, more accurate approach for the
actual measured scale of the problem, after empirically finding exactly
where the more complex approach's precision breaks down first.

## Scalability path

The right architecture depends on scale *and shape*, not just "the KB got
bigger." Three distinct tiers:

**Tier 1 — where this repo is now.** Single tenant (Northstar), ~2,200
tokens total. Full-context inclusion + prompt caching. Retrieval has
nothing meaningful to add at this size.

**Tier 2 — Northstar grows organically.** More properties, more service
lines, more edge-case policies, still one client. Once the KB crosses
roughly 20-30K tokens, or document count grows into the dozens with real
topical overlap (more docs competing for words like "cancellation" — the
exact pattern found and fixed above), that's the signal to revisit
retrieval. Not because the context window can't hold it, but because
relevance ranking starts mattering again at that density. `search.py` is
built, tested, and ready for this transition.

**Tier 3 — acquisition by a much larger chain.** A different *shape* of
problem, not a bigger version of Tier 2. Nobody wants every property's
policies in every ticket's context regardless of window size — the real
need is a **routing layer**: which brand, property, or region does this
ticket even belong to? If tickets carry reliable metadata (property ID,
brand tag), that's simple filtering, no ML required. Retrieval only
re-enters the picture *within* the correctly-scoped subset, and only if
that subset is itself large — a two-layer architecture (route, then
retrieve), not a single bigger index.
