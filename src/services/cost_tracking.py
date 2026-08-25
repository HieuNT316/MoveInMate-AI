"""Cost tracking for LLM and embedding API usage.

Inserts usage records into `usage_logs` table with calculated costs based on
token usage from API responses.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.database import SessionLocal

logger = logging.getLogger(__name__)

# Pricing (USD per 1M tokens as of 2024)
OPENAI_GPT4O_MINI_INPUT = Decimal("0.15")   # $0.15 / 1M input tokens
OPENAI_GPT4O_MINI_OUTPUT = Decimal("0.60")  # $0.60 / 1M output tokens

GOOGLE_EMBEDDING_INPUT = Decimal("0.0001")   # $0.0001 / 1M tokens (generous estimate)


def calculate_chat_cost(input_tokens: int, output_tokens: int) -> Decimal:
    """Calculate cost for chat completion."""
    input_cost = (Decimal(input_tokens) / 1_000_000) * OPENAI_GPT4O_MINI_INPUT
    output_cost = (Decimal(output_tokens) / 1_000_000) * OPENAI_GPT4O_MINI_OUTPUT
    return input_cost + output_cost


def calculate_embedding_cost(tokens: int) -> Decimal:
    """Calculate cost for embedding."""
    return (Decimal(tokens) / 1_000_000) * GOOGLE_EMBEDDING_INPUT


def log_usage(
    user_id: int | None,
    provider: str,
    model: str,
    operation: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Log API usage for cost tracking into `usage_logs` table."""
    db = SessionLocal()
    try:
        cost = Decimal("0")
        if operation == "chat" and input_tokens is not None and output_tokens is not None:
            cost = calculate_chat_cost(input_tokens, output_tokens)
        elif operation == "embedding" and input_tokens is not None:
            cost = calculate_embedding_cost(input_tokens)

        stmt = text("""
            INSERT INTO usage_logs (user_id, provider, model, operation, input_tokens, output_tokens, cost_usd)
            VALUES (:user_id, :provider, :model, :operation, :input_tokens, :output_tokens, :cost)
        """)
        db.execute(stmt, {
            "user_id": user_id,
            "provider": provider,
            "model": model,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": float(cost),
        })
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log usage: {e}")
    finally:
        db.close()


def get_usage_summary(
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    """Get usage summary for dashboard."""
    db = SessionLocal()
    try:
        query = """
            SELECT
                provider,
                model,
                operation,
                COUNT(*) as request_count,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cost_usd) as total_cost
            FROM usage_logs
            WHERE 1=1
        """
        params = {}
        if user_id:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        if date_from:
            query += " AND created_at >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND created_at <= :date_to"
            params["date_to"] = date_to

        query += " GROUP BY provider, model, operation ORDER BY total_cost DESC"

        result = db.execute(text(query), params)
        rows = [dict(row._mapping) for row in result.fetchall()]

        total_cost = sum(row["total_cost"] or 0 for row in rows)

        return {
            "total_cost": total_cost,
            "breakdown": rows,
        }
    finally:
        db.close()
