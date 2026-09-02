"""Fail-closed owner authentication for the private control API."""
from __future__ import annotations

import secrets

from fastapi import HTTPException, Request

from .settings import settings


def require_owner(request: Request) -> str:
    """Accept a verified Google ID token, or an internal owner key for setup.

    The owner key is never exposed by the web application. It exists for the
    private connector and operational recovery only. A deployment without an
    identity configuration is intentionally unusable for mutations.
    """
    internal_key = request.headers.get("x-fpl-owner-key", "")
    if settings.owner_access_key and secrets.compare_digest(internal_key, settings.owner_access_key):
        return "owner-key"
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer ") or not (settings.owner_email and settings.google_oauth_client_id):
        raise HTTPException(status_code=401, detail="owner_authentication_required")
    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(authorization.removeprefix("Bearer "), requests.Request(), settings.google_oauth_client_id)
    except Exception as error:
        raise HTTPException(status_code=401, detail="owner_identity_invalid") from error
    email = str(claims.get("email") or "").casefold()
    if not claims.get("email_verified") or not secrets.compare_digest(email, settings.owner_email):
        raise HTTPException(status_code=403, detail="owner_not_allowlisted")
    return email
