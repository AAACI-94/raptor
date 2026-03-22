"""Health check endpoint."""

import logging

from fastapi import APIRouter

from app.core.config import settings
from app.core.database import check_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Health check with database and API key probes."""
    db_ok = check_db()
    api_key_set = bool(settings.anthropic_api_key)

    status = "ok" if db_ok and api_key_set else "degraded"
    checks = {
        "database": "connected" if db_ok else "disconnected",
        "anthropic_api_key": "configured" if api_key_set else "missing",
    }

    if status == "degraded":
        logger.warning("[health] Degraded: %s", checks)

    return {
        "status": status,
        "version": settings.version,
        "checks": checks,
    }
