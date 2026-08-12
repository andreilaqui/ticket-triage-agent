"""
CMS authentication: a single shared username/password gate, read from
environment variables. No user table, no database, no session cookies -
this is the "simplistic login" scoped deliberately, not a corner cut.

Two details that matter more than they look like they should:

1. secrets.compare_digest, not `==`. Python's `==` on strings compares
   character-by-character and stops at the first mismatch, so a guess
   that gets more characters right takes measurably longer to reject
   than one that's wrong immediately - an attacker can exploit that
   timing difference to guess a password one character at a time.
   compare_digest always takes the same time regardless of where (or
   whether) two strings differ, closing that side channel.

2. Both compare_digest calls run unconditionally, not inside a
   short-circuiting `or`. If username and password were checked as
   `if not compare_digest(...) or not compare_digest(...)`, a wrong
   username would skip the password check entirely - which itself leaks
   timing information about whether the username was even close. Both
   checks always run here, every time, regardless of the outcome of the
   other.
"""

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def require_cms_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """FastAPI dependency - add `Depends(require_cms_auth)` to any route
    that should be gated behind the CMS login. Returns the authenticated
    username on success; raises HTTPException otherwise."""
    correct_username = os.environ.get("CMS_USERNAME")
    correct_password = os.environ.get("CMS_PASSWORD")

    if not correct_username or not correct_password:
        raise HTTPException(
            status_code=500,
            detail="CMS_USERNAME / CMS_PASSWORD not configured on the server.",
        )

    username_ok = secrets.compare_digest(credentials.username, correct_username)
    password_ok = secrets.compare_digest(credentials.password, correct_password)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
