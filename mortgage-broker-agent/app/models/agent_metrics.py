"""
Agent execution metrics and cost estimates.
"""
import os
from datetime import datetime
from app.models.database import get_db


def _rate_per_token(env_name: str, default_per_million: str) -> float:
    return float(os.environ.get(env_name, default_per_million)) / 1_000_000


def estimate_cost(input_tokens: int, output_tokens: int) -> dict:
    """Estimate Anthropic spend using configurable per-1M token rates."""
    input_rate = _rate_per_token("ANTHROPIC_INPUT_COST_PER_1M", "3.00")
    output_rate = _rate_per_token("ANTHROPIC_OUTPUT_COST_PER_1M", "15.00")
    input_cost = input_tokens * input_rate
    output_cost = output_tokens * output_rate
    return {
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": input_cost + output_cost,
    }


def record_agent_run(
    session_id: str,
    model: str,
    status: str,
    stage: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    error: str = "",
):
    costs = estimate_cost(input_tokens, output_tokens)
    conn = get_db()
    conn.execute(
        """
        INSERT INTO agent_runs (
            session_id, model, status, stage,
            input_tokens, output_tokens, total_tokens,
            input_cost_usd, output_cost_usd, total_cost_usd,
            latency_ms, error, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            model,
            status,
            stage,
            input_tokens,
            output_tokens,
            input_tokens + output_tokens,
            costs["input_cost_usd"],
            costs["output_cost_usd"],
            costs["total_cost_usd"],
            latency_ms,
            error[:1000],
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def get_agent_metrics(limit: int = 50) -> dict:
    conn = get_db()
    summary = conn.execute(
        """
        SELECT
            COUNT(*) AS total_runs,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successful_runs,
            SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) AS failed_runs,
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(total_tokens), 0) AS total_tokens,
            COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd,
            COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
        FROM agent_runs
        """
    ).fetchone()
    by_model = conn.execute(
        """
        SELECT
            model,
            COUNT(*) AS runs,
            COALESCE(SUM(total_tokens), 0) AS total_tokens,
            COALESCE(SUM(total_cost_usd), 0) AS total_cost_usd,
            COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
        FROM agent_runs
        GROUP BY model
        ORDER BY total_cost_usd DESC, runs DESC
        """
    ).fetchall()
    recent = conn.execute(
        """
        SELECT
            id, session_id, model, status, stage,
            input_tokens, output_tokens, total_tokens,
            total_cost_usd, latency_ms, error, created_at
        FROM agent_runs
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    return {
        "summary": dict(summary),
        "by_model": [dict(row) for row in by_model],
        "recent_runs": [dict(row) for row in recent],
        "pricing": {
            "input_per_1m": float(os.environ.get("ANTHROPIC_INPUT_COST_PER_1M", "3.00")),
            "output_per_1m": float(os.environ.get("ANTHROPIC_OUTPUT_COST_PER_1M", "15.00")),
            "currency": "USD",
            "estimate": True,
        },
    }
