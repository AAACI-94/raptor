"""Health check endpoint."""

import logging

from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_db
from app.services.ai.ollama import check_ollama
from app.services.ai.claude_cli import check_claude_cli

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Health check with database and AI provider probes."""
    db_ok = check_db()
    api_key_set = bool(settings.anthropic_api_key)
    ollama_ok = check_ollama()
    cli_ok = check_claude_cli()

    # At least one AI provider must be available
    ai_ok = api_key_set or cli_ok or ollama_ok
    status = "ok" if db_ok and ai_ok else "degraded"

    # Determine active provider (matches router auto-detection order)
    if settings.raptor_provider != "auto":
        provider = settings.raptor_provider
    elif api_key_set:
        provider = "anthropic"
    elif cli_ok:
        provider = "claude-cli"
    elif ollama_ok:
        provider = "ollama"
    else:
        provider = "none"

    checks = {
        "database": "connected" if db_ok else "disconnected",
        "anthropic_api_key": "configured" if api_key_set else "missing",
        "claude_cli": "available" if cli_ok else "unavailable",
        "ollama": f"available ({settings.raptor_ollama_model})" if ollama_ok else "unavailable",
        "active_provider": provider,
    }

    if status == "degraded":
        logger.warning("[health] Degraded: %s", checks)

    return {
        "status": status,
        "version": settings.version,
        "checks": checks,
    }
