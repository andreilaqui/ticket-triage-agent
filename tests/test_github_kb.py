"""
Tests for github_kb.py. All httpx calls are mocked - no real GitHub API
calls, no GITHUB_TOKEN needed to run these. A few tests (filename
validation) don't even need mocking, since that check happens before
any network call is made.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import base64

import httpx
import pytest

import github_kb


class _FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


def test_valid_filenames_match_local_knowledge_base():
    filenames = github_kb.list_valid_doc_filenames()
    assert "tours-shuttles-booking.md" in filenames
    assert len(filenames) == 8


def test_get_doc_content_rejects_unknown_filename():
    # No mocking needed - this check happens before any network call.
    with pytest.raises(ValueError):
        github_kb.get_doc_content("../../etc/passwd")


def test_update_doc_content_rejects_unknown_filename():
    with pytest.raises(ValueError):
        github_kb.update_doc_content("not-a-real-doc.md", "new text", "sha123", "tester")


def test_get_doc_content_decodes_base64_correctly(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO", "fake-repo")

    fake_content = "# Test Doc\nSome content here."
    encoded = base64.b64encode(fake_content.encode("utf-8")).decode("utf-8")

    def fake_get(url, headers):
        return _FakeResponse(200, {"content": encoded, "sha": "abc123"})

    monkeypatch.setattr(httpx, "get", fake_get)

    result = github_kb.get_doc_content("pet-policy.md")
    assert result.content == fake_content
    assert result.sha == "abc123"
    assert result.filename == "pet-policy.md"


def test_update_doc_content_sends_correct_payload(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO", "fake-repo")

    captured = {}

    def fake_put(url, headers, json):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(200, {})

    monkeypatch.setattr(httpx, "put", fake_put)

    github_kb.update_doc_content(
        "pet-policy.md", "new content here", "current-sha-456", "cmsadmin"
    )

    assert "pet-policy.md" in captured["url"]
    assert captured["json"]["sha"] == "current-sha-456"
    assert "cmsadmin" in captured["json"]["message"]
    decoded = base64.b64decode(captured["json"]["content"]).decode("utf-8")
    assert decoded == "new content here"


def test_update_doc_content_raises_clear_error_on_sha_conflict(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO", "fake-repo")

    def fake_put(url, headers, json):
        return _FakeResponse(409, {})

    monkeypatch.setattr(httpx, "put", fake_put)

    with pytest.raises(RuntimeError, match="changed by someone else"):
        github_kb.update_doc_content("pet-policy.md", "new content", "stale-sha", "cmsadmin")
