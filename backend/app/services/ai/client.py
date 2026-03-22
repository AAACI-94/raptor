"""Anthropic API client with model routing, token tracking, and OTel instrumentation."""

import json
import logging
import time
import uuid
from typing import Any

import anthropic

from app.core.config import settings
from app.core.database import get_db
from app.core.telemetry import agent_span, record_llm_call

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (March 2026)
MODEL_PRICING = {
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}


class AnthropicClient:
    """Wrapper around the Anthropic SDK with instrumentation."""

    def __init__(self):
        self._client: anthropic.Anthropic | None = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        agent_role: str = "unknown",
        project_id: str | None = None,
        operation: str = "completion",
    ) -> dict[str, Any]:
        """Non-streaming completion with full instrumentation.

        Returns dict with: content, model, input_tokens, output_tokens, cost_usd, duration_ms
        """
        with agent_span(agent_role, operation, project_id=project_id) as span:
            start = time.monotonic()

            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools

            try:
                response = self.client.messages.create(**kwargs)
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error("[ai-client] Completion failed: %s", e)
                raise

            duration_ms = int((time.monotonic() - start) * 1000)

            # Extract content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    content += json.dumps({"tool": block.name, "input": block.input})

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
            cache_write = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # OTel instrumentation
            record_llm_call(
                span, model, input_tokens, output_tokens,
                temperature=temperature, max_tokens=max_tokens,
                finish_reason=response.stop_reason or "end_turn",
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
            )
            span.set_attribute("raptor.duration_ms", duration_ms)
            span.set_attribute("raptor.cost_usd", cost)

            # Record token usage in DB
            if project_id:
                self._record_usage(
                    project_id, agent_role, operation, model,
                    input_tokens, output_tokens, cache_read, cache_write, cost,
                    span.get_span_context().trace_id if span.get_span_context() else None,
                )

            logger.info(
                "[ai-client] %s.%s: %s, %d in / %d out, $%.4f, %dms",
                agent_role, operation, model, input_tokens, output_tokens, cost, duration_ms,
            )

            return {
                "content": content,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write,
                "cost_usd": cost,
                "duration_ms": duration_ms,
                "stop_reason": response.stop_reason,
            }

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a completion."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Fallback: assume sonnet pricing
            pricing = MODEL_PRICING["claude-sonnet-4-20250514"]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _record_usage(
        self, project_id: str, agent: str, operation: str, model: str,
        input_tokens: int, output_tokens: int, cache_read: int, cache_write: int,
        cost: float, trace_id: int | None,
    ) -> None:
        """Record token usage in the database."""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO token_usage (id, project_id, agent, operation, model,
                   input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                   estimated_cost_usd, trace_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), project_id, agent, operation, model,
                 input_tokens, output_tokens, cache_read, cache_write, cost,
                 hex(trace_id) if trace_id else None),
            )
            db.commit()
        except Exception as e:
            logger.warning("[ai-client] Failed to record token usage: %s", e)


# Singleton
ai_client = AnthropicClient()
