"""
Tests for main.py. Only load_tickets is testable without a live API call -
run_ticket and main() both call the real agent, which needs a key and
costs (tiny amounts of) real money. Those are verified manually - see
README's Setup section.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import DEFAULT_TICKETS_PATH, load_tickets


def test_loads_sample_tickets_as_list_of_dicts():
    tickets = load_tickets(DEFAULT_TICKETS_PATH)
    assert isinstance(tickets, list)
    assert len(tickets) > 0
    for t in tickets:
        assert "id" in t
        assert "message" in t


def test_every_sample_ticket_has_unique_id():
    tickets = load_tickets(DEFAULT_TICKETS_PATH)
    ids = [t["id"] for t in tickets]
    assert len(ids) == len(set(ids))
