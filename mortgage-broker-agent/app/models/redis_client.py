import os
import redis
import json
import logging
from typing import Optional, Dict, Any

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT", "1")),
    socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "1")),
)


SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 60 * 60 * 24))  # 24 hours


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


def save_session(session_id: str, data: Dict[str, Any]) -> bool:
    try:
        redis_client.setex(
            _session_key(session_id),
            SESSION_TTL_SECONDS,
            json.dumps(data),
        )
        return True
    except redis.RedisError as exc:
        logger.warning("Redis save failed for session %s: %s", session_id, exc)
        return False


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    try:
        raw = redis_client.get(_session_key(session_id))
    except redis.RedisError as exc:
        logger.warning("Redis read failed for session %s: %s", session_id, exc)
        return None

    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Redis session payload is invalid JSON for %s", session_id)
        return None


def delete_session(session_id: str) -> bool:
    try:
        redis_client.delete(_session_key(session_id))
        return True
    except redis.RedisError as exc:
        logger.warning("Redis delete failed for session %s: %s", session_id, exc)
        return False
