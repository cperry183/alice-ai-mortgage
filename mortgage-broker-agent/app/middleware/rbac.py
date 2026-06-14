"""
Enhanced RBAC Decorators & Middleware — Mortgage Broker Agent
Route-level permission enforcement with structured audit logging.

Aligned to:
- NIST AI RMF: Govern (role-based access control)
- OWASP LLM Top 10: LLM06 (controlled agent behavior via role scoping)
"""

import functools
import logging
from typing import Callable, Optional, Set, Union
from datetime import datetime

from flask import request, jsonify, current_app, g
from flask_login import current_user, login_required

from app.models.auth import ROLE_PERMISSIONS
from app.models.database import get_db

# ─────────────────────────────────────────────────────────────
#  Audit Logging
# ─────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)


def _client_ip() -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    return forwarded_for.split(",", 1)[0].strip() or request.remote_addr or ""


def log_permission_check(
    user_id: str,
    permission: str,
    allowed: bool,
    target_id: Optional[str] = None,
    detail: Optional[str] = None,
):
    """
    Audit log for permission checks (success AND failure).
    Helps detect permission escalation attempts.
    """
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO audit_log (user_id, action, target_id, detail, ip_address)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                f"permission_{'granted' if allowed else 'denied'}:{permission}",
                target_id,
                detail or request.path,
                _client_ip(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Also log to application logger at appropriate level
    level = logging.INFO if allowed else logging.WARNING
    logger.log(
        level,
        f"Permission {'granted' if allowed else 'denied'}: {permission} for user {user_id} at {request.path}",
    )


# ─────────────────────────────────────────────────────────────
#  Enhanced Permission Decorators
# ─────────────────────────────────────────────────────────────


def permission_required(
    *permissions: str,
    require_all: bool = False,
    roles: Optional[Set[str]] = None,
):
    """
    Enforce permission-based access control on routes.

    Usage:
        @app.route("/admin/metrics")
        @permission_required("agent_metrics:read")
        def get_metrics():
            ...

        # Multiple permissions (any)
        @permission_required("borrowers:read", "borrowers:update")
        def borrow_operations():
            ...

        # Multiple permissions (all required)
        @permission_required("borrowers:read", "documents:generate", require_all=True)
        def complex_operation():
            ...

        # Role-based check
        @permission_required(roles={"admin"})
        def admin_only():
            ...
    """
    if not permissions and not roles:
        raise ValueError("Must specify either permissions or roles")

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        @login_required
        def wrapper(*args, **kwargs):
            user = current_user

            # Check role constraint if specified
            if roles and user.role not in roles:
                log_permission_check(
                    user.id,
                    f"role_check:{user.role}",
                    False,
                    detail=f"Required roles: {roles}",
                )
                return jsonify({"error": "Forbidden"}), 403

            # Check permission constraint if specified
            if permissions:
                if require_all:
                    # User must have ALL permissions
                    if not all(user.can(perm) for perm in permissions):
                        missing = [p for p in permissions if not user.can(p)]
                        log_permission_check(
                            user.id,
                            f"permission_check:all",
                            False,
                            detail=f"Missing: {missing}",
                        )
                        return jsonify({"error": "Forbidden"}), 403
                else:
                    # User must have ANY permission
                    if not any(user.can(perm) for perm in permissions):
                        log_permission_check(
                            user.id,
                            f"permission_check:any",
                            False,
                            detail=f"Required any of: {list(permissions)}",
                        )
                        return jsonify({"error": "Forbidden"}), 403

            # Log successful permission check
            granted_perms = [p for p in permissions if user.can(p)]
            log_permission_check(
                user.id,
                f"permission_check:{'all' if require_all else 'any'}",
                True,
                detail=f"Granted: {granted_perms}",
            )

            return handler(*args, **kwargs)

        return wrapper

    return decorator


def role_required(*allowed_roles: str):
    """
    Enforce role-based access control on routes.

    Usage:
        @app.route("/admin/users")
        @role_required("admin")
        def manage_users():
            ...

        # Multiple roles (any)
        @role_required("admin", "manager")
        def supervisory_task():
            ...
    """
    if not allowed_roles:
        raise ValueError("Must specify at least one role")

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        @login_required
        def wrapper(*args, **kwargs):
            user = current_user

            if user.role not in allowed_roles:
                log_permission_check(
                    user.id,
                    f"role_required:{user.role}",
                    False,
                    detail=f"Required one of: {allowed_roles}",
                )
                return jsonify({"error": "Forbidden"}), 403

            log_permission_check(
                user.id, f"role_required:{user.role}", True, detail=f"Role: {user.role}"
            )

            return handler(*args, **kwargs)

        return wrapper

    return decorator


def audit_action(action: str, target_id_param: Optional[str] = None):
    """
    Audit log for state-changing actions (POST, PUT, DELETE, PATCH).

    Usage:
        @app.route("/api/borrowers/<session_id>", methods=["PUT"])
        @permission_required("borrowers:update")
        @audit_action("update_borrower", target_id_param="session_id")
        def update_borrower_handler(session_id):
            ...
    """

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            target_id = None
            if target_id_param:
                target_id = kwargs.get(target_id_param) or request.args.get(
                    target_id_param
                )

            conn = get_db()
            try:
                conn.execute(
                    """
                    INSERT INTO audit_log (user_id, action, target_id, detail, ip_address)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        current_user.id if current_user.is_authenticated else "anonymous",
                        action,
                        target_id,
                        request.method,
                        _client_ip(),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            logger.info(
                f"Action audited: {action} on {target_id} by {current_user.id if current_user.is_authenticated else 'anonymous'}"
            )

            return handler(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_per_role(
    max_requests: dict[str, int],
    window_seconds: int = 60,
):
    """
    Rate limiting decorator with per-role request quotas.

    Usage:
        @rate_limit_per_role(
            max_requests={"admin": 1000, "broker": 100},
            window_seconds=60
        )
        @app.route("/api/chat", methods=["POST"])
        def chat():
            ...
    """

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Unauthorized"}), 401

            user_role = current_user.role
            limit = max_requests.get(user_role, max_requests.get("default", 100))

            # Use Flask's g object to track per-request state
            # In production, use Redis or Memcached
            conn = get_db()
            try:
                cutoff = datetime.utcnow().timestamp() - window_seconds

                # Clean old entries
                conn.execute(
                    "DELETE FROM audit_log WHERE user_id = ? AND created_at < datetime(?)",
                    (current_user.id, datetime.fromtimestamp(cutoff).isoformat()),
                )

                # Count recent requests
                count = conn.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE user_id = ? AND created_at > datetime(?, '-' || ? || ' seconds')",
                    (current_user.id, datetime.utcnow().isoformat(), window_seconds),
                ).fetchone()[0]

                if count >= limit:
                    logger.warning(
                        f"Rate limit exceeded for {user_role} user {current_user.id}: {count}/{limit}"
                    )
                    return jsonify({"error": "Rate limit exceeded"}), 429

                conn.commit()
            finally:
                conn.close()

            return handler(*args, **kwargs)

        return wrapper

    return decorator


def require_content_type(*allowed_types: str):
    """
    Validate request Content-Type header.

    Usage:
        @require_content_type("application/json")
        @app.route("/api/documents/generate", methods=["POST"])
        def generate():
            ...
    """
    if not allowed_types:
        allowed_types = ("application/json",)

    def decorator(handler: Callable) -> Callable:
        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            content_type = request.headers.get("Content-Type", "").lower()
            if not any(ct in content_type for ct in allowed_types):
                logger.warning(
                    f"Invalid Content-Type: {content_type} from {_client_ip()} for {request.path}"
                )
                return jsonify({"error": "Invalid Content-Type"}), 400

            return handler(*args, **kwargs)

        return wrapper

    return decorator


# ─────────────────────────────────────────────────────────────
#  Before-Request Middleware
# ─────────────────────────────────────────────────────────────


def init_rbac_middleware(app):
    """Initialize RBAC middleware in Flask app."""

    @app.before_request
    def before_request_rbac():
        """
        Pre-flight checks:
        - Reject requests with invalid headers
        - Set up audit context
        - Check for suspicious patterns
        """
        # Reject obviously malicious request sizes
        if request.content_length and request.content_length > 10 * 1024 * 1024:
            logger.warning(
                f"Oversized request from {_client_ip()}: {request.content_length} bytes"
            )
            return jsonify({"error": "Payload too large"}), 413

        # Store audit context in Flask's g object (request-scoped)
        g.request_id = request.headers.get("X-Request-ID", "")
        g.client_ip = _client_ip()
        g.timestamp = datetime.utcnow()

        # Log suspicious HTTP methods
        if request.method not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
            logger.warning(
                f"Suspicious HTTP method: {request.method} from {g.client_ip} for {request.path}"
            )

    @app.after_request
    def after_request_rbac(response):
        """
        Post-response logging and security headers.
        """
        # Log non-2xx responses at warning level
        if response.status_code >= 400:
            logger.warning(
                f"{request.method} {request.path} {response.status_code} from {g.get('client_ip', 'unknown')}"
            )

        # Audit trail for sensitive operations
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            detail = f"{request.method} {request.path} => {response.status_code}"
            if current_user.is_authenticated:
                log_permission_check(
                    current_user.id,
                    f"audit_trail:{request.method}",
                    response.status_code < 400,
                    detail=detail,
                )

        return response

    return app
