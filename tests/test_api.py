"""
Tests for api.py - the HTTP <-> function translation, not the agent's
actual answers (those are covered by test_guardrails.py and manual
testing, which need a live key). triage_ticket is mocked here entirely,
so these run free and fast, and verify only that requests map to the
right call and responses come back correctly shaped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

import api
from agent import TriageResult


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # Runs before every test in this file, not just the rate-limit one -
    # otherwise an earlier test's /tickets calls could leave the shared
    # limiter partway "used up," causing a later, unrelated test to fail
    # with a confusing 429 instead of the 200 it actually expects.
    api.limiter.reset()
    yield


def test_health_check():
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200


def test_rejects_empty_message():
    client = TestClient(api.app)
    response = client.post("/tickets", json={"message": "   "})
    assert response.status_code == 400


def test_resolved_ticket_maps_to_correct_response_shape(monkeypatch):
    fake_result = TriageResult(
        action="resolved",
        category="test_category",
        reply="a test reply",
        cited_docs=["some-doc.md"],
    )
    monkeypatch.setattr(api, "triage_ticket", lambda text: fake_result)

    client = TestClient(api.app)
    response = client.post(
        "/tickets", json={"message": "test ticket", "ticket_id": "T-999"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "T-999"
    assert body["action"] == "resolved"
    assert body["reply"] == "a test reply"
    assert body["cited_docs"] == ["some-doc.md"]
    assert body["escalation_reason"] is None


def test_escalated_ticket_maps_to_correct_response_shape(monkeypatch):
    fake_result = TriageResult(
        action="escalated",
        category="test_category",
        escalation_reason="a test reason",
    )
    monkeypatch.setattr(api, "triage_ticket", lambda text: fake_result)

    client = TestClient(api.app)
    response = client.post("/tickets", json={"message": "test ticket"})

    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "escalated"
    assert body["escalation_reason"] == "a test reason"
    assert body["reply"] is None


def test_guest_ui_served_at_root():
    client = TestClient(api.app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Northstar Rockies" in response.text


def test_tickets_endpoint_rate_limits_after_threshold(monkeypatch):
    """10/minute is the configured limit (see api.py)."""
    fake_result = TriageResult(
        action="resolved", category="test", reply="ok", cited_docs=[]
    )
    monkeypatch.setattr(api, "triage_ticket", lambda text: fake_result)

    client = TestClient(api.app)
    statuses = [
        client.post("/tickets", json={"message": "test"}).status_code
        for _ in range(15)
    ]

    assert statuses.count(200) <= 10
    assert 429 in statuses
