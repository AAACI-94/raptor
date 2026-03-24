"""AI provider router: Anthropic API, Claude CLI, or Ollama.

Resolution order for "auto" mode:
1. If ANTHROPIC_API_KEY is set, use Anthropic API (fastest, most capable)
2. If Claude CLI is installed and authenticated, use Claude CLI (no API key needed)
3. If Ollama is running with the configured model, use Ollama (free, local)
4. Raise an error
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_resolved_provider: str | None = None


def get_provider() -> str:
    """Resolve which AI provider to use. Cached after first call."""
    global _resolved_provider
    if _resolved_provider is not None:
        return _resolved_provider

    mode = settings.raptor_provider

    if mode == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("RAPTOR_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        _resolved_provider = "anthropic"

    elif mode == "claude-cli":
        from app.services.ai.claude_cli import check_claude_cli
        if not check_claude_cli():
            raise RuntimeError("RAPTOR_PROVIDER=claude-cli but claude binary not found or not authenticated")
        _resolved_provider = "claude-cli"

    elif mode == "ollama":
        from app.services.ai.ollama import check_ollama
        if not check_ollama():
            raise RuntimeError(f"RAPTOR_PROVIDER=ollama but Ollama is not running or {settings.raptor_ollama_model} is not available")
        _resolved_provider = "ollama"

    else:  # auto
        if settings.anthropic_api_key:
            _resolved_provider = "anthropic"
            logger.info("[ai-router] Auto-selected provider: anthropic (API key configured)")
        else:
            from app.services.ai.claude_cli import check_claude_cli
            if check_claude_cli():
                _resolved_provider = "claude-cli"
                logger.info("[ai-router] Auto-selected provider: claude-cli (binary found, keychain auth)")
            else:
                from app.services.ai.ollama import check_ollama
                if check_ollama():
                    _resolved_provider = "ollama"
                    logger.info("[ai-router] Auto-selected provider: ollama (%s available locally)", settings.raptor_ollama_model)
                else:
                    raise RuntimeError(
                        "No AI provider available. Options:\n"
                        "  1. Set ANTHROPIC_API_KEY for Anthropic API\n"
                        "  2. Install Claude CLI (npm i -g @anthropic-ai/claude-code) for keychain auth\n"
                        f"  3. Start Ollama with '{settings.raptor_ollama_model}' (ollama pull {settings.raptor_ollama_model})"
                    )

    return _resolved_provider


def complete(
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
    """Route a completion to the active provider."""
    provider = get_provider()

    if provider == "anthropic":
        from app.services.ai.client import ai_client
        return ai_client.complete(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
            temperature=temperature, tools=tools, agent_role=agent_role,
            project_id=project_id, operation=operation,
        )
    elif provider == "claude-cli":
        from app.services.ai.claude_cli import claude_cli_client
        return claude_cli_client.complete(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
            temperature=temperature, tools=tools, agent_role=agent_role,
            project_id=project_id, operation=operation,
        )
    else:  # ollama
        from app.services.ai.ollama import ollama_client
        return ollama_client.complete(
            messages=messages, model=model, system=system, max_tokens=max_tokens,
            temperature=temperature, tools=tools, agent_role=agent_role,
            project_id=project_id, operation=operation,
        )


def reset_provider() -> None:
    """Reset cached provider (for testing or config changes)."""
    global _resolved_provider
    _resolved_provider = None
