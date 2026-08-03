"""
BM25 keyword search over the knowledge base.

Design note: knowledge base files are read fresh from disk on every
search call, not cached in memory. At this corpus size (a handful of
short markdown files) the cost is negligible, and it avoids serving
stale content after a doc gets edited. See README's "Design decisions"
section for the full reasoning.

Scope note: this module finds the most relevant *document(s)* for a
query. It does not chunk documents into sections. If a doc contains two
competing policies (e.g. standard refund vs. weather-hold refund),
picking the right one is the agent's job when it reads the doc content -
not search's job. Worth knowing where that line sits.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"


@dataclass
class SearchResult:
    filename: str
    score: float
    content: str


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace.

    Deliberately simple - no stemming, no stopword removal. This means
    "cancelled" and "cancellation" are treated as unrelated tokens. Good
    enough for a small, hand-written corpus; worth knowing as a real
    limitation, not something to quietly assume away.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def _strip_see_also(text: str) -> str:
    """Remove the '## See Also' section (and everything after it) before
    a document is tokenized for indexing.

    Cross-reference notes are written for human readers and for the agent
    to use as a recovery hint if it lands on the wrong doc - but mentioning
    another doc's topic, even just to rule it out, still reads as evidence
    *for* a keyword match under BM25. Stripping this section before
    indexing keeps each doc's vocabulary focused on what it's actually
    about. The full document, See Also included, is still what gets
    returned to the caller (see search_knowledge_base) - only the
    index-time tokenization excludes it.
    """
    marker = "## See Also"
    idx = text.find(marker)
    return text if idx == -1 else text[:idx]


def _load_documents() -> list[tuple[str, str]]:
    """Read every .md file in knowledge_base/ fresh off disk.

    Returns a list of (filename, content) pairs. Intentionally no
    caching - see module docstring.
    """
    return [
        (path.name, path.read_text(encoding="utf-8"))
        for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    ]


def search_knowledge_base(query: str, top_k: int = 3) -> list[SearchResult]:
    """Return up to top_k KB docs relevant to query, ranked by BM25 score.

    Docs scoring 0 (no shared vocabulary with the query at all) are
    excluded rather than padding out top_k with noise - an empty result
    is a valid, honest answer, not a bug to work around.
    """
    docs = _load_documents()
    if not docs:
        return []

    filenames = [name for name, _ in docs]
    contents = [content for _, content in docs]  # full text, returned as-is
    tokenized_corpus = [_tokenize(_strip_see_also(content)) for content in contents]

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(
        zip(filenames, scores, contents), key=lambda row: row[1], reverse=True
    )

    results = [
        SearchResult(filename=fname, score=float(score), content=content)
        for fname, score, content in ranked
        if score > 0
    ]
    return results[:top_k]


if __name__ == "__main__":
    # Manual smoke test: `python search.py <your query here>`
    import sys

    query = " ".join(sys.argv[1:]) or "what's the price of the glacier tour"
    print(f"Query: {query!r}\n")
    results = search_knowledge_base(query)
    if not results:
        print("  (no matches)")
    for r in results:
        print(f"  {r.filename}  (score: {r.score:.3f})")
