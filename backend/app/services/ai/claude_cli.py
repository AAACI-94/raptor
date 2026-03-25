"""Claude CLI provider: uses the local `claude` binary's keychain auth.

No ANTHROPIC_API_KEY needed. Shells out to `claude -p` with stream-json output.
Uses the same interface as AnthropicClient and OllamaClient for drop-in routing.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.telemetry import agent_span, record_llm_call

logger = logging.getLogger(__name__)

# Model name mapping: RAPTOR model names -> claude CLI model aliases
CLI_MODEL_MAP = {
    "claude-opus-4-20250514": "opus",
    "claude-sonnet-4-20250514": "sonnet",
    "claude-haiku-4-5-20251001": "haiku",
}

# Pricing (same as Anthropic API)
MODEL_PRICING = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.80, "output": 4.00},
}

_resolved_binary: str | None = None
_binary_searched = False


def _find_claude_binary() -> str | None:
    """Find the claude CLI binary. Searched once and cached."""
    global _resolved_binary, _binary_searched
    if _binary_searched:
        return _resolved_binary
    _binary_searched = True

    # 1. Check PATH
    binary = shutil.which("claude")
    if binary:
        _resolved_binary = binary
        logger.info("[claude-cli] Found on PATH: %s", binary)
        return binary

    # 2. Check nvm versions
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for ver_dir in nvm_dir.iterdir():
            candidate = ver_dir / "bin" / "claude"
            if candidate.exists():
                _resolved_binary = str(candidate)
                logger.info("[claude-cli] Found in nvm: %s", _resolved_binary)
                return _resolved_binary

    # 3. Check ~/.claude/local/bin/claude
    local_bin = Path.home() / ".claude" / "local" / "bin" / "claude"
    if local_bin.exists():
        _resolved_binary = str(local_bin)
        logger.info("[claude-cli] Found local install: %s", _resolved_binary)
        return _resolved_binary

    # 4. Check Claude desktop app (macOS)
    app_dir = Path.home() / "Library" / "Application Support" / "Claude" / "claude-code"
    if app_dir.exists():
        versions = sorted(app_dir.iterdir(), reverse=True)
        for ver_dir in versions:
            candidate = ver_dir / "claude"
            if candidate.exists():
                _resolved_binary = str(candidate)
                logger.info("[claude-cli] Found desktop app binary: %s", _resolved_binary)
                return _resolved_binary

    logger.warning("[claude-cli] Binary not found")
    return None


def check_claude_cli() -> bool:
    """Check if Claude CLI is available and authenticated."""
    binary = _find_claude_binary()
    if not binary:
        return False

    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and len(result.stdout.strip()) > 0
    except Exception:
        return False


class ClaudeCliClient:
    """Claude CLI client with the same interface as AnthropicClient/OllamaClient."""

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict] | None = None,
        agent_role: str = "unknown",
        project_id: str | None = None,
        operation: str = "completion",
    ) -> dict[str, Any]:
        """Non-streaming completion via Claude CLI.

        Returns the same dict shape as AnthropicClient.complete.
        """
        binary = _find_claude_binary()
        if not binary:
            raise RuntimeError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")

        cli_model = self._resolve_model(model)
        prompt = self._format_messages(messages, system)

        with agent_span(agent_role, operation, project_id=project_id) as span:
            start = time.monotonic()

            try:
                result = subprocess.run(
                    [
                        binary, "-p",
                        "--output-format", "stream-json",
                        "--verbose",
                        "--no-session-persistence",
                        "--model", cli_model,
                        "--max-turns", "1",
                        "--allowedTools", "",
                        "--setting-sources", "",
                    ],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            except subprocess.TimeoutExpired:
                span.set_attribute("error", True)
                span.set_attribute("error.message", "Claude CLI timeout (300s)")
                raise RuntimeError("Claude CLI timed out after 300s")
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                logger.error("[claude-cli] Spawn failed: %s", e)
                raise

            duration_ms = int((time.monotonic() - start) * 1000)

            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else f"Exit code {result.returncode}"
                span.set_attribute("error", True)
                span.set_attribute("error.message", error_msg)
                logger.error("[claude-cli] %s.%s failed: %s", agent_role, operation, error_msg)
                raise RuntimeError(f"Claude CLI error: {error_msg}")

            # Parse NDJSON output
            content = self._parse_result(result.stdout)

            # Estimate tokens (CLI doesn't always report them)
            input_tokens = len(prompt.split()) * 2  # rough estimate
            output_tokens = len(content.split()) * 2

            cost = self._calculate_cost(cli_model, input_tokens, output_tokens)

            # OTel instrumentation
            record_llm_call(
                span, f"claude-cli/{cli_model}", input_tokens, output_tokens,
                temperature=temperature, max_tokens=max_tokens,
                finish_reason="end_turn",
            )
            span.set_attribute("raptor.duration_ms", duration_ms)
            span.set_attribute("raptor.cost_usd", cost)
            span.set_attribute("raptor.provider", "claude-cli")

            # Record usage in DB
            if project_id:
                self._record_usage(
                    project_id, agent_role, operation, f"claude-cli/{cli_model}",
                    input_tokens, output_tokens, cost,
                    span.get_span_context().trace_id if span.get_span_context() else None,
                )

            logger.info(
                "[claude-cli] %s.%s: %s, ~%d in / ~%d out, $%.4f, %dms",
                agent_role, operation, cli_model, input_tokens, output_tokens, cost, duration_ms,
            )

            return {
                "content": content,
                "model": f"claude-cli/{cli_model}",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": cost,
                "duration_ms": duration_ms,
                "stop_reason": "end_turn",
            }

    def _resolve_model(self, model: str) -> str:
        """Map full model name to CLI alias."""
        return CLI_MODEL_MAP.get(model, "sonnet")

    def _format_messages(self, messages: list[dict[str, str]], system: str = "") -> str:
        """Convert messages to a single prompt string for the CLI.

        System messages wrapped in <instructions> tags.
        """
        parts: list[str] = []

        if system:
            parts.append(f"<instructions>\n{system}\n\nIMPORTANT: Respond with text only. Do NOT use any tools, function calls, or XML tool invocations. Output your response directly as text.\n</instructions>")

        system_msgs = [m for m in messages if m.get("role") == "system"]
        conv_msgs = [m for m in messages if m.get("role") != "system"]

        for msg in system_msgs:
            parts.append(f"<instructions>\n{msg['content']}\n</instructions>")

        if len(conv_msgs) == 1 and conv_msgs[0]["role"] == "user":
            parts.append(conv_msgs[0]["content"])
        else:
            for msg in conv_msgs:
                role = "Human" if msg["role"] == "user" else "Assistant"
                parts.append(f"{role}: {msg['content']}")

        return "\n\n".join(parts)

    def _parse_result(self, stdout: str) -> str:
        """Parse NDJSON output from Claude CLI and extract the final result."""
        lines = stdout.strip().split("\n")
        for line in lines:
            try:
                obj = json.loads(line)
                if obj.get("type") == "result":
                    if obj.get("is_error"):
                        raise RuntimeError(f"Claude CLI error: {obj.get('result', 'Unknown')}")
                    return obj.get("result", "")
            except json.JSONDecodeError:
                continue

        # Fallback: try to find assistant message content
        for line in lines:
            try:
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    message = obj.get("message", {})
                    content = message.get("content", "")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        return "".join(
                            block.get("text", "") for block in content
                            if block.get("type") == "text"
                        )
            except json.JSONDecodeError:
                continue

        logger.warning("[claude-cli] No result found in %d lines of output", len(lines))
        return ""

    def _calculate_cost(self, cli_model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on CLI model alias."""
        pricing = MODEL_PRICING.get(cli_model, MODEL_PRICING["sonnet"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _record_usage(
        self, project_id: str, agent: str, operation: str, model: str,
        input_tokens: int, output_tokens: int, cost: float, trace_id: int | None,
    ) -> None:
        """Record token usage in the database."""
        import uuid
        try:
            from app.core.database import get_db
            db = get_db()
            db.execute(
                """INSERT INTO token_usage (id, project_id, agent, operation, model,
                   input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                   estimated_cost_usd, trace_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)""",
                (str(uuid.uuid4()), project_id, agent, operation, model,
                 input_tokens, output_tokens, cost,
                 hex(trace_id) if trace_id else None),
            )
            db.commit()
        except Exception as e:
            logger.warning("[claude-cli] Failed to record token usage: %s", e)


# Singleton
claude_cli_client = ClaudeCliClient()
