"""
Tests for the /cms/docs endpoints in api.py. github_kb is mocked
entirely - these test the HTTP wiring and auth gating, not real GitHub
API behavior (that's covered separately in test_github_kb.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import api
import github_kb
from github_kb import DocContent

AUTH = ("testuser", "testpass")


def _client(monkeypatch):
    monkeypatch.setenv("CMS_USERNAME", "testuser")
    monkeypatch.setenv("CMS_PASSWORD", "testpass")
    return TestClient(api.app)


def test_list_docs_requires_auth(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/cms/docs")
    assert response.status_code == 401


def test_list_docs_returns_filenames(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(
        github_kb, "list_valid_doc_filenames", lambda: ["a.md", "b.md"]
    )
    response = client.get("/cms/docs", auth=AUTH)
    assert response.status_code == 200
    assert response.json()["filenames"] == ["a.md", "b.md"]


def test_get_doc_requires_auth(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/cms/docs/pet-policy.md")
    assert response.status_code == 401


def test_get_doc_returns_content_and_sha(monkeypatch):
    client = _client(monkeypatch)
    fake_doc = DocContent(filename="pet-policy.md", content="fake content", sha="abc123")
    monkeypatch.setattr(github_kb, "get_doc_content", lambda filename: fake_doc)

    response = client.get("/cms/docs/pet-policy.md", auth=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "fake content"
    assert body["sha"] == "abc123"


def test_get_unknown_doc_returns_404(monkeypatch):
    client = _client(monkeypatch)

    def raise_value_error(filename):
        raise ValueError(f"'{filename}' is not a known knowledge base doc.")

    monkeypatch.setattr(github_kb, "get_doc_content", raise_value_error)
    response = client.get("/cms/docs/not-real.md", auth=AUTH)
    assert response.status_code == 404


def test_update_doc_requires_auth(monkeypatch):
    client = _client(monkeypatch)
    response = client.put(
        "/cms/docs/pet-policy.md", json={"content": "x", "sha": "y"}
    )
    assert response.status_code == 401


def test_update_doc_succeeds(monkeypatch):
    client = _client(monkeypatch)
    captured = {}

    def fake_update(filename, new_content, sha, edited_by):
        captured["filename"] = filename
        captured["content"] = new_content
        captured["sha"] = sha
        captured["edited_by"] = edited_by

    monkeypatch.setattr(github_kb, "update_doc_content", fake_update)

    response = client.put(
        "/cms/docs/pet-policy.md",
        json={"content": "updated text", "sha": "sha123"},
        auth=AUTH,
    )
    assert response.status_code == 200
    assert captured["filename"] == "pet-policy.md"
    assert captured["content"] == "updated text"
    assert captured["edited_by"] == "testuser"  # from the authenticated session


def test_update_doc_conflict_returns_409(monkeypatch):
    client = _client(monkeypatch)

    def raise_conflict(filename, new_content, sha, edited_by):
        raise RuntimeError("This doc was changed by someone else since you loaded it.")

    monkeypatch.setattr(github_kb, "update_doc_content", raise_conflict)

    response = client.put(
        "/cms/docs/pet-policy.md",
        json={"content": "x", "sha": "stale-sha"},
        auth=AUTH,
    )
    assert response.status_code == 409
