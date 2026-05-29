import json
import os
import secrets
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


security = HTTPBearer(auto_error=False)


def _configured_tokens() -> dict[str, str]:
    raw = os.environ.get("AGENT_SERVICE_TOKENS", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(role): str(token) for role, token in parsed.items() if token}
        except json.JSONDecodeError:
            tokens: dict[str, str] = {}
            for pair in raw.split(","):
                if ":" not in pair:
                    continue
                role, token = pair.split(":", 1)
                if role.strip() and token.strip():
                    tokens[role.strip()] = token.strip()
            if tokens:
                return tokens

    token = os.environ.get("AGENT_SERVICE_TOKEN", "").strip()
    if token:
        return {"orchestrator": token}
    return {}


def require_agent_role(*allowed_roles: str) -> Callable:
    allowed = set(allowed_roles)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> str:
        tokens = _configured_tokens()
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent RBAC is not configured",
            )
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing agent bearer token",
            )

        for role, token in tokens.items():
            if secrets.compare_digest(credentials.credentials, token) and role in allowed:
                return role

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent role is not authorized for this operation",
        )

    return dependency


def agent_auth_headers(role: str = "orchestrator") -> dict[str, str]:
    token = _configured_tokens().get(role)
    return {"Authorization": f"Bearer {token}"} if token else {}
