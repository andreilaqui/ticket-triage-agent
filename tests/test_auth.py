"""
Tests for auth.py's require_cms_auth dependency. All free/local - no
API keys or external services involved, since auth is self-contained.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from fastapi.testclient import TestClient

import api
from auth import require_cms_auth


def test_fails_clearly_when_not_configured(monkeypatch):
    monkeypatch.delenv("CMS_USERNAME", raising=False)
    monkeypatch.delenv("CMS_PASSWORD", raising=False)
    creds = HTTPBasicCredentials(username="anyone", password="anything")
    with pytest.raises(HTTPException) as exc_info:
        require_cms_auth(creds)
    assert exc_info.value.status_code == 500


def test_accepts_correct_credentials(monkeypatch):
    monkeypatch.setenv("CMS_USERNAME", "testuser")
    monkeypatch.setenv("CMS_PASSWORD", "testpass")
    creds = HTTPBasicCredentials(username="testuser", password="testpass")
    assert require_cms_auth(creds) == "testuser"


def test_rejects_wrong_password(monkeypatch):
    monkeypatch.setenv("CMS_USERNAME", "testuser")
    monkeypatch.setenv("CMS_PASSWORD", "testpass")
    creds = HTTPBasicCredentials(username="testuser", password="wrongpass")
    with pytest.raises(HTTPException) as exc_info:
        require_cms_auth(creds)
    assert exc_info.value.status_code == 401


def test_rejects_wrong_username(monkeypatch):
    monkeypatch.setenv("CMS_USERNAME", "testuser")
    monkeypatch.setenv("CMS_PASSWORD", "testpass")
    creds = HTTPBasicCredentials(username="wronguser", password="testpass")
    with pytest.raises(HTTPException) as exc_info:
        require_cms_auth(creds)
    assert exc_info.value.status_code == 401


def test_cms_route_requires_auth_end_to_end(monkeypatch):
    """Full HTTP wiring, not just the dependency in isolation - confirms
    the route is actually protected, not just that the function works."""
    monkeypatch.setenv("CMS_USERNAME", "testuser")
    monkeypatch.setenv("CMS_PASSWORD", "testpass")
    client = TestClient(api.app)

    no_auth = client.get("/cms")
    assert no_auth.status_code == 401

    wrong_auth = client.get("/cms", auth=("testuser", "wrongpass"))
    assert wrong_auth.status_code == 401

    correct_auth = client.get("/cms", auth=("testuser", "testpass"))
    assert correct_auth.status_code == 200
    assert "Knowledge Base" in correct_auth.text
