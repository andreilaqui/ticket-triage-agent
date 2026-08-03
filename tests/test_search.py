"""
Basic tests for search.py.

Honest caveat: with only one knowledge base doc drafted so far, these
tests can prove the search *mechanics* work (indexing, scoring,
filtering, ranking) but can't yet prove it correctly discriminates
between multiple competing documents - that needs more KB docs in
place first. Worth adding cross-document tests once the KB grows.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from search import search_knowledge_base


def test_finds_relevant_doc_for_tour_pricing_query():
    results = search_knowledge_base("glacier skywalk tour price")
    assert len(results) > 0
    assert results[0].filename == "tours-shuttles-booking.md"


def test_returns_nothing_for_completely_unrelated_query():
    results = search_knowledge_base("xyzzy quantum flavor nonsense")
    assert len(results) == 0


def test_scores_are_sorted_descending():
    results = search_knowledge_base("refund cancellation tour shuttle")
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
