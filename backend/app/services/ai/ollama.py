"""Ollama client for local LLM inference (qwen3.5)."""

import json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.telemetry import agent_span, record_llm_call

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen3.5"


def _get_ollama_url() -> str:
    """Get Ollama URL from config (not hardcoded, supports Docker networking)."""
    return settings.raptor_ollama_url
# qwen3.5 is a reasoning model; it generates thinking tokens that take time.
TIMEOUT = 300.0


class OllamaClient:
    """Ollama API client with instrumentation matching AnthropicClient interface."""

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str = DEFAULT_MODEL,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        agent_role: str = "unknown",
        project_id: str | None = None,
        operation: str = "completion",
    ) -> dict[str, Any]:
        """Non-streaming completion via Ollama /api/chat.

        Returns the same dict shape as AnthropicClient.complete for drop-in use.
        """
        # Resolve model: if it's a claude model name, map to qwen3.5
        ollama_model = self._resolve_model(model)

        with agent_span(agent_role, operation, project_id=project_id) as span:
            start = time.monotonic()

            # Build Ollama message format
            ollama_messages = []
            if system:
                ollama_messages.append({"role": "system", "content": system})
            ollama_messages.extend(messages)

            payload = {
                "model": ollama_model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            try:
                resp = httpx.post(
                    f"{_get_ollama_url()}/api/chat",
                    json=payload,
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error("[ollama] Completion failed: %s", e)
                raise

            duration_ms = int((time.monotonic() - start) * 1000)

            content = data.get("message", {}).get("content", "")

            # Strip thinking tags from qwen3.5 output
            content = self._strip_thinking(content)

            # Token counts from Ollama response
            input_tokens = data.get("prompt_eval_count", 0)
            output_tokens = data.get("eval_count", 0)

            # OTel instrumentation
            record_llm_call(
                span, ollama_model, input_tokens, output_tokens,
                temperature=temperature, max_tokens=max_tokens,
                finish_reason="stop",
            )
            span.set_attribute("raptor.duration_ms", duration_ms)
            span.set_attribute("raptor.cost_usd", 0.0)
            span.set_attribute("raptor.provider", "ollama")

            # Record token usage in DB (cost = 0 for local)
            if project_id:
                self._record_usage(
                    project_id, agent_role, operation, ollama_model,
                    input_tokens, output_tokens,
                    span.get_span_context().trace_id if span.get_span_context() else None,
                )

            logger.info(
                "[ollama] %s.%s: %s, %d in / %d out, $0.00, %dms",
                agent_role, operation, ollama_model, input_tokens, output_tokens, duration_ms,
            )

            return {
                "content": content,
                "model": ollama_model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": 0.0,
                "duration_ms": duration_ms,
                "stop_reason": "stop",
            }

    def _resolve_model(self, model: str) -> str:
        """Map Claude model names to the local Ollama model."""
        if model.startswith("claude-"):
            return settings.raptor_ollama_model
        return model

    def _strip_thinking(self, content: str) -> str:
        """Strip <think>...</think> tags from qwen3.5 reasoning output."""
        import re
        return re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()

    def _record_usage(
        self, project_id: str, agent: str, operation: str, model: str,
        input_tokens: int, output_tokens: int, trace_id: int | None,
    ) -> None:
        """Record token usage in the database (cost = 0 for local)."""
        import uuid
        try:
            from app.core.database import get_db
            db = get_db()
            db.execute(
                """INSERT INTO token_usage (id, project_id, agent, operation, model,
                   input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                   estimated_cost_usd, trace_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0.0, ?)""",
                (str(uuid.uuid4()), project_id, agent, operation, model,
                 input_tokens, output_tokens,
                 hex(trace_id) if trace_id else None),
            )
            db.commit()
        except Exception as e:
            logger.warning("[ollama] Failed to record token usage: %s", e)


def check_ollama() -> bool:
    """Check if Ollama is running and has the required model."""
    try:
        resp = httpx.get(f"{_get_ollama_url()}/api/tags", timeout=5.0)
        if resp.status_code != 200:
            return False
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        target = settings.raptor_ollama_model
        return any(target in m for m in models)
    except Exception:
        return False


# Singleton
ollama_client = OllamaClient()
