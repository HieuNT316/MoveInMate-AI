"""Tests for cost tracking service."""

from decimal import Decimal

from src.services.cost_tracking import (
    calculate_chat_cost,
    calculate_embedding_cost,
    get_usage_summary,
    log_usage,
)


class TestCalculateChatCost:
    """Test calculate_chat_cost function."""

    def test_gpt4o_mini_typical_tokens(self):
        """GPT-4o-mini cost for typical request."""
        # 1000 input + 500 output
        cost = calculate_chat_cost(1000, 500)
        expected = Decimal("1000") / Decimal("1_000_000") * Decimal("0.15") + \
                   Decimal("500") / Decimal("1_000_000") * Decimal("0.60")
        assert cost == expected

    def test_gpt4o_mini_zero_tokens(self):
        """Zero tokens returns zero cost."""
        assert calculate_chat_cost(0, 0) == Decimal("0")

    def test_gpt4o_mini_large_input(self):
        """Large input token count."""
        # 1M input tokens = $0.15, 0 output = $0
        cost = calculate_chat_cost(1_000_000, 0)
        assert cost == Decimal("0.15")

    def test_gpt4o_mini_large_output(self):
        """Large output token count."""
        # 0 input = $0, 1M output tokens = $0.60
        cost = calculate_chat_cost(0, 1_000_000)
        assert cost == Decimal("0.60")

    def test_cost_type_is_decimal(self):
        """Return type is Decimal."""
        cost = calculate_chat_cost(100, 50)
        assert isinstance(cost, Decimal)


class TestCalculateEmbeddingCost:
    """Test calculate_embedding_cost function."""

    def test_typical_embedding(self):
        """Embedding cost for typical request."""
        # 1000 tokens
        cost = calculate_embedding_cost(1000)
        expected = Decimal("1000") / Decimal("1_000_000") * Decimal("0.0001")
        assert cost == expected

    def test_zero_tokens(self):
        """Zero tokens returns zero cost."""
        assert calculate_embedding_cost(0) == Decimal("0")

    def test_large_embedding(self):
        """Large embedding (1M tokens)."""
        cost = calculate_embedding_cost(1_000_000)
        assert cost == Decimal("0.0001")

    def test_cost_type_is_decimal(self):
        """Return type is Decimal."""
        cost = calculate_embedding_cost(500)
        assert isinstance(cost, Decimal)


class TestLogUsage:
    """Test log_usage function with fake DB."""

    def test_log_chat_usage(self, fake_auth_provisioning):
        """Log chat usage inserts record."""
        log_usage(
            user_id=1,
            provider="openai",
            model="gpt-4o-mini",
            operation="chat",
            input_tokens=1000,
            output_tokens=500,
        )
        summary = get_usage_summary(user_id=1)
        assert summary["total_cost"] > 0
        assert len(summary["breakdown"]) == 1
        assert summary["breakdown"][0]["operation"] == "chat"
        assert summary["breakdown"][0]["model"] == "gpt-4o-mini"

    def test_log_embedding_usage(self, fake_auth_provisioning):
        """Log embedding usage inserts record."""
        log_usage(
            user_id=1,
            provider="google",
            model="gemini-embedding-001",
            operation="embedding",
            input_tokens=1000,
        )
        summary = get_usage_summary(user_id=1)
        assert summary["total_cost"] >= 0
        assert any(r["operation"] == "embedding" for r in summary["breakdown"])

    def test_log_usage_no_user(self, fake_auth_provisioning):
        """Log usage with null user_id (e.g., unauthenticated)."""
        log_usage(
            user_id=None,
            provider="openai",
            model="gpt-4o-mini",
            operation="chat",
            input_tokens=100,
            output_tokens=50,
        )
        summary = get_usage_summary()
        assert summary["total_cost"] > 0

    def test_log_usage_none_tokens_skips_cost(self, fake_auth_provisioning):
        """Log usage with null tokens does not compute cost."""
        # This should not raise - the function handles None gracefully
        log_usage(
            user_id=1,
            provider="openai",
            model="gpt-4o-mini",
            operation="chat",
            input_tokens=None,
            output_tokens=None,
        )
        summary = get_usage_summary(user_id=1)
        # Cost should be 0 since no tokens
        assert summary["total_cost"] == 0


class TestGetUsageSummary:
    """Test get_usage_summary function."""

    def test_empty_summary(self, fake_auth_provisioning):
        """Empty usage returns zero cost."""
        summary = get_usage_summary()
        assert summary["total_cost"] == 0
        assert summary["breakdown"] == []

    def test_summary_with_multiple_records(self, fake_auth_provisioning):
        """Multiple records aggregate correctly."""
        log_usage(user_id=1, provider="openai", model="gpt-4o-mini",
                  operation="chat", input_tokens=1000, output_tokens=500)
        log_usage(user_id=1, provider="openai", model="gpt-4o-mini",
                  operation="chat", input_tokens=2000, output_tokens=1000)
        log_usage(user_id=2, provider="google", model="gemini-embedding-001",
                  operation="embedding", input_tokens=500)

        summary = get_usage_summary(user_id=1)
        assert summary["total_cost"] > 0
        assert len(summary["breakdown"]) == 1
        assert summary["breakdown"][0]["request_count"] == 2
        assert summary["breakdown"][0]["total_input_tokens"] == 3000
        assert summary["breakdown"][0]["total_output_tokens"] == 1500

    def test_summary_all_users(self, fake_auth_provisioning):
        """Summary without user_id includes all users."""
        log_usage(user_id=1, provider="openai", model="gpt-4o-mini",
                  operation="chat", input_tokens=1000, output_tokens=500)
        log_usage(user_id=2, provider="google", model="gemini-embedding-001",
                  operation="embedding", input_tokens=500)

        summary = get_usage_summary()
        assert summary["total_cost"] > 0
        assert len(summary["breakdown"]) == 2

    def test_summary_breakdown_ordered_by_cost(self, fake_auth_provisioning):
        """Breakdown is ordered by cost descending."""
        # chat: 100 input + 50 output ~= $0.000045
        # embedding 1M tokens = $0.0001
        # embedding is more expensive, so it should come first
        log_usage(user_id=1, provider="openai", model="gpt-4o-mini",
                  operation="chat", input_tokens=100, output_tokens=50)
        log_usage(user_id=1, provider="google", model="gemini-embedding-001",
                  operation="embedding", input_tokens=1_000_000)

        summary = get_usage_summary(user_id=1)
        assert len(summary["breakdown"]) == 2
        # Embedding costs $0.0001, chat costs ~$0.000045 — embedding first
        assert summary["breakdown"][0]["operation"] == "embedding"
