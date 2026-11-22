"""Local-mode authentication and tenant-scoped authorization dependencies."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status

from .config import Settings

ALL_SCOPES = frozenset(
    {
        "projects:read",
        "projects:write",
        "tasks:read",
        "tasks:write",
        "profiles:read",
        "usage:read",
    }
)


@dataclass(frozen=True)
class Principal:
    """Authenticated caller with an explicit tenant and scope set.

    Attributes:
        tenant_id: Tenant the caller is authorized for.
        subject: Stable identifier of the authenticated identity.
        scopes: Permissions granted to this identity.

    """

    tenant_id: str
    subject: str
    scopes: frozenset[str]


def app_settings(request: Request) -> Settings:
    """Return settings attached to the FastAPI application.

    Args:
        request: Incoming request.

    Returns:
        Validated settings instance.

    """
    return request.app.state.settings


def require_principal(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Principal:
    """Authenticate a bearer token using constant-time comparison.

    Args:
        request: Incoming request carrying application settings.
        authorization: ``Authorization`` header value.

    Returns:
        Principal scoped to the configured local tenant.

    Raises:
        HTTPException: When the token is missing or invalid.

    """
    settings = app_settings(request)
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    supplied = authorization.removeprefix("Bearer ")
    expected = settings.api_token
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(tenant_id=settings.tenant_id, subject="local-bootstrap", scopes=ALL_SCOPES)


def require_scope(*scopes: str) -> Callable[..., Principal]:
    """Build a dependency that requires all named scopes.

    Args:
        *scopes: Scope strings that must all be present.

    Returns:
        FastAPI dependency returning the authenticated principal.

    """

    def dependency(
        principal: Principal = Depends(require_principal),
    ) -> Principal:
        if not set(scopes).issubset(principal.scopes):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return principal

    return dependency
