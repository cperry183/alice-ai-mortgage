"""
Scoped Service Identity System — Agent Microservices
Non-Human Identity (NHI) management with token lifecycle control.

Implements:
- Service account creation & lifecycle management
- Scoped bearer token generation with expiration
- Token rotation policies
- Service identity audit trails
- Least privilege token scoping by role and resource

Aligned to:
- NIST AI RMF: Govern (scoped agent identities)
- OWASP LLM Top 10: LLM06 (controlled agent behavior via scoped identity)
"""

import os
import secrets
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict

from app.models.database import get_db

# ─────────────────────────────────────────────────────────────
#  Database Schema Initialization
# ─────────────────────────────────────────────────────────────


def init_service_identity_db():
    """Create tables for service accounts and tokens."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS service_accounts (
            id                  TEXT PRIMARY KEY,
            name                TEXT NOT NULL UNIQUE,
            description         TEXT DEFAULT '',
            role                TEXT NOT NULL,
            status              TEXT DEFAULT 'active' CHECK(status IN ('active', 'suspended', 'revoked')),
            max_token_age_hours INTEGER DEFAULT 24,
            created_by          TEXT NOT NULL,
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now')),
            metadata_json       TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS service_tokens (
            id                  TEXT PRIMARY KEY,
            service_account_id  TEXT NOT NULL,
            token_hash          TEXT NOT NULL UNIQUE,
            description         TEXT DEFAULT '',
            scopes              TEXT NOT NULL,
            status              TEXT DEFAULT 'active' CHECK(status IN ('active', 'expired', 'revoked')),
            issued_at           TEXT DEFAULT (datetime('now')),
            expires_at          TEXT NOT NULL,
            last_used_at        TEXT,
            revoked_at          TEXT,
            revoked_by          TEXT,
            metadata_json       TEXT DEFAULT '{}',
            FOREIGN KEY (service_account_id) REFERENCES service_accounts(id)
        );

        CREATE TABLE IF NOT EXISTS service_token_audit (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            service_account_id  TEXT,
            token_id            TEXT,
            action              TEXT NOT NULL,
            detail              TEXT,
            ip_address          TEXT,
            created_at          TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (service_account_id) REFERENCES service_accounts(id),
            FOREIGN KEY (token_id) REFERENCES service_tokens(id)
        );

        CREATE INDEX IF NOT EXISTS idx_service_accounts_role ON service_accounts(role);
        CREATE INDEX IF NOT EXISTS idx_service_accounts_status ON service_accounts(status);
        CREATE INDEX IF NOT EXISTS idx_service_tokens_account ON service_tokens(service_account_id);
        CREATE INDEX IF NOT EXISTS idx_service_tokens_status ON service_tokens(status);
        CREATE INDEX IF NOT EXISTS idx_service_token_audit_account ON service_token_audit(service_account_id);
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
#  Data Models
# ─────────────────────────────────────────────────────────────


@dataclass
class ServiceToken:
    """Bearer token issued to a service account."""

    id: str
    service_account_id: str
    token_hash: str
    description: str
    scopes: List[str]
    status: str
    issued_at: str
    expires_at: str
    last_used_at: Optional[str]
    revoked_at: Optional[str]
    revoked_by: Optional[str]
    metadata: Dict

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return (
            self.status == "active"
            and datetime.fromisoformat(self.expires_at) > datetime.utcnow()
        )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.fromisoformat(self.expires_at) <= datetime.utcnow()

    def to_dict(self, include_hash: bool = False) -> Dict:
        """Convert to dictionary, optionally excluding sensitive fields."""
        data = asdict(self)
        if not include_hash:
            data["token_hash"] = "***REDACTED***"
        return data


@dataclass
class ServiceAccount:
    """Non-human identity for agent services."""

    id: str
    name: str
    description: str
    role: str
    status: str
    max_token_age_hours: int
    created_by: str
    created_at: str
    updated_at: str
    metadata: Dict

    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == "active"

    def to_dict(self, include_sensitive: bool = False) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


# ─────────────────────────────────────────────────────────────
#  Service Account Management
# ─────────────────────────────────────────────────────────────


def create_service_account(
    name: str,
    role: str,
    created_by: str,
    description: str = "",
    max_token_age_hours: int = 24,
    metadata: Optional[Dict] = None,
) -> Tuple[bool, Optional[str], str]:
    """
    Create a new service account (Non-Human Identity).

    Returns:
        (success: bool, account_id: Optional[str], message: str)
    """
    if not name or not role:
        return False, None, "name and role are required"

    if role not in {"admin", "broker", "orchestrator"}:
        return False, None, f"Invalid role: {role}"

    account_id = str(uuid.uuid4())
    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO service_accounts
            (id, name, description, role, max_token_age_hours, created_by, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                name,
                description,
                role,
                max_token_age_hours,
                created_by,
                __import__("json").dumps(metadata or {}),
            ),
        )
        conn.commit()
        return True, account_id, f"Service account '{name}' created successfully"
    except sqlite3.IntegrityError as e:
        return False, None, f"Account creation failed: {str(e)}"
    finally:
        conn.close()


def get_service_account(account_id: str) -> Optional[ServiceAccount]:
    """Retrieve service account by ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM service_accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if not row:
            return None

        return ServiceAccount(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            role=row["role"],
            status=row["status"],
            max_token_age_hours=row["max_token_age_hours"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=__import__("json").loads(row["metadata_json"]),
        )
    finally:
        conn.close()


def list_service_accounts(
    role: Optional[str] = None, status: str = "active"
) -> List[ServiceAccount]:
    """List service accounts, optionally filtered by role and status."""
    conn = get_db()
    try:
        if role:
            rows = conn.execute(
                "SELECT * FROM service_accounts WHERE role = ? AND status = ? ORDER BY created_at DESC",
                (role, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM service_accounts WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()

        return [
            ServiceAccount(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                role=row["role"],
                status=row["status"],
                max_token_age_hours=row["max_token_age_hours"],
                created_by=row["created_by"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=__import__("json").loads(row["metadata_json"]),
            )
            for row in rows
        ]
    finally:
        conn.close()


def suspend_service_account(account_id: str, reason: str = "") -> Tuple[bool, str]:
    """Suspend a service account (revoke all existing tokens)."""
    conn = get_db()
    try:
        # Mark account as suspended
        conn.execute(
            "UPDATE service_accounts SET status = 'suspended', updated_at = datetime('now') WHERE id = ?",
            (account_id,),
        )

        # Revoke all active tokens for this account
        conn.execute(
            "UPDATE service_tokens SET status = 'revoked', revoked_at = datetime('now') WHERE service_account_id = ? AND status = 'active'",
            (account_id,),
        )

        # Audit trail
        conn.execute(
            "INSERT INTO service_token_audit (service_account_id, action, detail) VALUES (?, ?, ?)",
            (account_id, "account_suspended", reason),
        )

        conn.commit()
        return True, f"Service account suspended and {account_id} tokens revoked"
    except Exception as e:
        return False, f"Failed to suspend account: {str(e)}"
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
#  Token Management (Lifecycle Control)
# ─────────────────────────────────────────────────────────────


def _hash_token(token: str) -> str:
    """Hash a token using SHA-256 for storage."""
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token() -> str:
    """Generate a cryptographically secure bearer token."""
    return f"sat_{secrets.token_urlsafe(64)}"


def issue_token(
    service_account_id: str,
    scopes: List[str],
    description: str = "",
    ttl_hours: Optional[int] = None,
) -> Tuple[bool, Optional[str], str]:
    """
    Issue a scoped bearer token for a service account.

    Args:
        service_account_id: The service account to issue token for
        scopes: List of resource scopes (e.g., ["pipeline:execute", "metrics:read"])
        description: Human-readable token description
        ttl_hours: Token time-to-live in hours (defaults to account's max_token_age_hours)

    Returns:
        (success: bool, token: Optional[str], message: str)
    """
    account = get_service_account(service_account_id)
    if not account:
        return False, None, "Service account not found"

    if not account.is_active():
        return False, None, f"Service account is {account.status}"

    if not scopes:
        return False, None, "At least one scope is required"

    token = _generate_token()
    token_hash = _hash_token(token)
    token_id = str(uuid.uuid4())

    ttl = ttl_hours or account.max_token_age_hours
    expires_at = datetime.utcnow() + timedelta(hours=ttl)

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO service_tokens
            (id, service_account_id, token_hash, description, scopes, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (token_id, service_account_id, token_hash, description, __import__("json").dumps(scopes), expires_at.isoformat()),
        )

        # Audit token issuance
        conn.execute(
            "INSERT INTO service_token_audit (service_account_id, token_id, action, detail) VALUES (?, ?, ?, ?)",
            (service_account_id, token_id, "token_issued", f"Scopes: {scopes}, TTL: {ttl}h"),
        )

        conn.commit()
        return True, token, f"Token issued successfully (expires in {ttl}h)"
    except Exception as e:
        return False, None, f"Token issuance failed: {str(e)}"
    finally:
        conn.close()


def verify_token(token: str) -> Tuple[bool, Optional[ServiceAccount], Optional[ServiceToken], str]:
    """
    Verify and validate a bearer token.

    Returns:
        (is_valid: bool, account: Optional[ServiceAccount], token_record: Optional[ServiceToken], message: str)
    """
    if not token or not token.startswith("sat_"):
        return False, None, None, "Invalid token format"

    token_hash = _hash_token(token)
    conn = get_db()

    try:
        # Find token record
        token_row = conn.execute(
            "SELECT * FROM service_tokens WHERE token_hash = ?", (token_hash,)
        ).fetchone()

        if not token_row:
            return False, None, None, "Token not found"

        # Parse token record
        token_record = ServiceToken(
            id=token_row["id"],
            service_account_id=token_row["service_account_id"],
            token_hash=token_row["token_hash"],
            description=token_row["description"],
            scopes=__import__("json").loads(token_row["scopes"]),
            status=token_row["status"],
            issued_at=token_row["issued_at"],
            expires_at=token_row["expires_at"],
            last_used_at=token_row["last_used_at"],
            revoked_at=token_row["revoked_at"],
            revoked_by=token_row["revoked_by"],
            metadata=__import__("json").loads(token_row["metadata_json"]),
        )

        # Check token validity
        if not token_record.is_valid():
            if token_record.is_expired():
                return False, None, token_record, "Token has expired"
            return False, None, token_record, f"Token is {token_record.status}"

        # Get associated account
        account = get_service_account(token_record.service_account_id)
        if not account or not account.is_active():
            return False, None, token_record, "Associated service account is not active"

        # Update last_used_at timestamp
        conn.execute(
            "UPDATE service_tokens SET last_used_at = datetime('now') WHERE id = ?",
            (token_record.id,),
        )
        conn.commit()

        return True, account, token_record, "Token verified successfully"
    finally:
        conn.close()


def revoke_token(token_id: str, revoked_by: str, reason: str = "") -> Tuple[bool, str]:
    """Revoke a specific token."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE service_tokens SET status = 'revoked', revoked_at = datetime('now'), revoked_by = ? WHERE id = ?",
            (revoked_by, token_id),
        )

        # Audit revocation
        token_row = conn.execute(
            "SELECT service_account_id FROM service_tokens WHERE id = ?", (token_id,)
        ).fetchone()
        if token_row:
            conn.execute(
                "INSERT INTO service_token_audit (service_account_id, token_id, action, detail) VALUES (?, ?, ?, ?)",
                (token_row["service_account_id"], token_id, "token_revoked", reason),
            )

        conn.commit()
        return True, f"Token {token_id} revoked successfully"
    except Exception as e:
        return False, f"Token revocation failed: {str(e)}"
    finally:
        conn.close()


def rotate_tokens(
    service_account_id: str, revoked_by: str
) -> Tuple[bool, Optional[str], str]:
    """
    Rotate all active tokens for a service account.
    Issues new token and revokes all old ones.
    """
    account = get_service_account(service_account_id)
    if not account:
        return False, None, "Service account not found"

    conn = get_db()
    try:
        # Get all active tokens to copy their scopes
        old_tokens = conn.execute(
            "SELECT * FROM service_tokens WHERE service_account_id = ? AND status = 'active'",
            (service_account_id,),
        ).fetchall()

        if not old_tokens:
            return False, None, "No active tokens to rotate"

        # Use scopes from first active token
        scopes = __import__("json").loads(old_tokens[0]["scopes"])

        # Generate new token
        new_token = _generate_token()
        new_token_hash = _hash_token(new_token)
        new_token_id = str(uuid.uuid4())

        ttl = account.max_token_age_hours
        expires_at = datetime.utcnow() + timedelta(hours=ttl)

        # Insert new token
        conn.execute(
            """
            INSERT INTO service_tokens
            (id, service_account_id, token_hash, description, scopes, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                new_token_id,
                service_account_id,
                new_token_hash,
                "Rotated token",
                __import__("json").dumps(scopes),
                expires_at.isoformat(),
            ),
        )

        # Revoke old tokens
        for old_token in old_tokens:
            conn.execute(
                "UPDATE service_tokens SET status = 'revoked', revoked_at = datetime('now'), revoked_by = ? WHERE id = ?",
                (revoked_by, old_token["id"]),
            )

        # Audit rotation
        conn.execute(
            "INSERT INTO service_token_audit (service_account_id, action, detail) VALUES (?, ?, ?)",
            (service_account_id, "tokens_rotated", f"Rotated {len(old_tokens)} tokens"),
        )

        conn.commit()
        return True, new_token, f"Tokens rotated successfully (new token expires in {ttl}h)"
    except Exception as e:
        return False, None, f"Token rotation failed: {str(e)}"
    finally:
        conn.close()


def get_token_audit_log(service_account_id: str, limit: int = 100) -> List[Dict]:
    """Get audit trail for a service account."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, service_account_id, token_id, action, detail, ip_address, created_at
            FROM service_token_audit
            WHERE service_account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (service_account_id, limit),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
#  Helper: Environment Configuration
# ─────────────────────────────────────────────────────────────


def configure_service_tokens_from_env() -> Dict[str, str]:
    """
    Read service token configuration from environment variables.
    Supports both JSON and colon-separated formats.

    Env var: AGENT_SERVICE_TOKENS='{"broker":"token1","admin":"token2"}'
    Or: AGENT_SERVICE_TOKENS='broker:token1,admin:token2'
    """
    import json

    raw = os.environ.get("AGENT_SERVICE_TOKENS", "").strip()
    if not raw:
        return {}

    # Try JSON format first
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(role): str(token) for role, token in parsed.items() if token}
    except json.JSONDecodeError:
        pass

    # Fall back to colon-separated format
    tokens = {}
    for pair in raw.split(","):
        if ":" not in pair:
            continue
        role, token = pair.split(":", 1)
        role = role.strip()
        token = token.strip()
        if role and token:
            tokens[role] = token

    return tokens
