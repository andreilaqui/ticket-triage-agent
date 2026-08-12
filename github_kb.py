"""
GitHub-backed persistence for knowledge base docs, via GitHub's Contents
API. Chosen over a database because Render's free tier can't persist
local file changes (see README's CMS section) - committing straight to
GitHub sidesteps that entirely. Since Render auto-deploys on push, a
save here becomes a real git commit AND a real (if delayed ~1-2 min)
production update, with a full audit trail for free - no separate
"edit history" feature needed, git already is one.

Scope constraint, and it's also a security boundary, not just a
feature limit: only filenames that already exist in knowledge_base/
locally are ever accepted. This rules out path traversal (a filename
like '../../../etc/passwd') by construction, not by trying to sanitize
untrusted input after the fact - see list_valid_doc_filenames().
"""

import base64
import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

from search import _load_documents  # reuse - same pattern agent.py uses

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"


def _github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN not set. See .env.example - needs a fine-grained "
            "GitHub PAT, Contents: Read and write, scoped to this repo only."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_and_owner() -> tuple[str, str]:
    owner = os.environ.get("GITHUB_OWNER")
    repo = os.environ.get("GITHUB_REPO")
    if not owner or not repo:
        raise RuntimeError("GITHUB_OWNER / GITHUB_REPO not set. See .env.example.")
    return owner, repo


def list_valid_doc_filenames() -> list[str]:
    """The whitelist. Only filenames that exist in the local
    knowledge_base/ directory are ever valid - this is what prevents
    path traversal, not string sanitization after the fact."""
    return sorted(name for name, _ in _load_documents())


@dataclass
class DocContent:
    filename: str
    content: str
    sha: str  # GitHub's blob sha - required to submit an update


def get_doc_content(filename: str) -> DocContent:
    if filename not in list_valid_doc_filenames():
        raise ValueError(f"'{filename}' is not a known knowledge base doc.")

    owner, repo = _repo_and_owner()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/knowledge_base/{filename}"

    try:
        response = httpx.get(url, headers=_github_headers())
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"GitHub API error fetching '{filename}': {e.response.status_code}"
        ) from e

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return DocContent(filename=filename, content=content, sha=data["sha"])


def update_doc_content(filename: str, new_content: str, sha: str, edited_by: str) -> None:
    """Commits new_content as an update to filename. sha must be the
    doc's current sha, from a prior get_doc_content() call - GitHub
    rejects the update (409) if it doesn't match, which is what
    prevents two people silently overwriting each other's edits. We
    never build our own locking - GitHub already does this for free."""
    if filename not in list_valid_doc_filenames():
        raise ValueError(f"'{filename}' is not a known knowledge base doc.")

    owner, repo = _repo_and_owner()
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/knowledge_base/{filename}"
    payload = {
        "message": f"CMS: update {filename} (by {edited_by})",
        "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
        "branch": "main",
    }

    try:
        response = httpx.put(url, headers=_github_headers(), json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise RuntimeError(
                "This doc was changed by someone else since you loaded "
                "it. Reload the latest version and try again."
            ) from e
        raise RuntimeError(
            f"GitHub API error updating '{filename}': {e.response.status_code}"
        ) from e