"""RAPTOR API: Research Authoring Platform with Traceable Orchestrated Reasoning."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.telemetry import init_telemetry
from app.core.logging_config import setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import health, projects, venues, artifacts, pipeline, observatory, exports, feedback

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle: init on startup, cleanup on shutdown."""
    setup_logging()
    logger.info("[main] RAPTOR v%s starting", settings.version)

    # Initialize database
    init_db()
    logger.info("[main] Database initialized")

    # Seed default publication target profiles
    from app.services.venue_service import seed_default_venues
    seed_default_venues()

    # Initialize telemetry
    init_telemetry()
    logger.info("[main] Telemetry initialized")

    # Register agents with pipeline orchestrator
    from app.services.pipeline.orchestrator import orchestrator
    from app.agents.research_strategist import ResearchStrategist
    from app.agents.structure_architect import StructureArchitect
    from app.agents.domain_writer import DomainWriter
    from app.agents.visual_architect import VisualArchitect
    from app.agents.critical_reviewer import CriticalReviewer
    from app.agents.production_agent import ProductionAgent

    orchestrator.register_agent("research_strategist", ResearchStrategist())
    orchestrator.register_agent("structure_architect", StructureArchitect())
    orchestrator.register_agent("domain_writer", DomainWriter())
    orchestrator.register_agent("visual_architect", VisualArchitect())
    orchestrator.register_agent("critical_reviewer", CriticalReviewer())
    orchestrator.register_agent("production_agent", ProductionAgent())
    logger.info("[main] All 6 agents registered")

    yield

    # Shutdown
    logger.info("[main] Shutting down")
    close_db()
    logger.info("[main] Shutdown complete")


app = FastAPI(
    title="RAPTOR",
    description="Research Authoring Platform with Traceable Orchestrated Reasoning",
    version=settings.version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5177"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware)

# Routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(venues.router, prefix="/api/publications", tags=["publications"])
app.include_router(venues.router, prefix="/api/venues", tags=["venues"])  # backwards compat alias
app.include_router(artifacts.router, prefix="/api", tags=["artifacts"])
app.include_router(pipeline.router, prefix="/api", tags=["pipeline"])
app.include_router(observatory.router, prefix="/api/observatory", tags=["observatory"])
app.include_router(exports.router, prefix="/api", tags=["exports"])
app.include_router(feedback.router, prefix="/api/observatory", tags=["feedback"])
