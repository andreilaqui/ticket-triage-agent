"""
Tests for agent.py and tools.py that don't require a live API call - no
ANTHROPIC_API_KEY needed to run these. Actually calling the agent against
real tickets is a manual step (see agent.py's __main__ block, or main.py
once it exists) since it costs real (if tiny) money and needs a real key.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import _load_full_knowledge_base, triage_ticket
from tools import ALL_TOOLS


def test_all_tools_have_required_schema_fields():
    for tool in ALL_TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"
        assert "required" in tool["input_schema"]


def test_exactly_two_tools_defined():
    # Deliberately no search_kb tool - see README's "Retrieval architecture"
    names = {t["name"] for t in ALL_TOOLS}
    assert names == {"draft_reply", "escalate"}


def test_full_knowledge_base_includes_every_doc():
    kb_text = _load_full_knowledge_base()
    kb_dir = Path(__file__).parent.parent / "knowledge_base"
    for doc_path in kb_dir.glob("*.md"):
        assert doc_path.name in kb_text


def test_triage_ticket_fails_clearly_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        triage_ticket("any ticket text")
        assert False, "expected RuntimeError when API key is missing"
    except RuntimeError as e:
        assert "ANTHROPIC_API_KEY" in str(e)
