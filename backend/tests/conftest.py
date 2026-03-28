"""Test fixtures for RAPTOR backend."""

import os
import pytest

# Set test environment before importing app modules
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""  # Disable OTel export in tests
os.environ["RAPTOR_RATE_LIMIT_DISABLED"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"  # Completely disable OTel SDK


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Create a fresh database for each test."""
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_PATH"] = db_path

    # Reset the global connection
    import app.core.database as db_module
    if db_module._connection is not None:
        try:
            db_module._connection.close()
        except Exception:
            pass
    db_module._connection = None

    # Force config reload with new DB path
    from app.core.config import Settings
    new_settings = Settings()
    import app.core.config as config_mod
    config_mod.settings = new_settings

    yield

    # Cleanup
    if db_module._connection is not None:
        try:
            db_module._connection.close()
        except Exception:
            pass
        db_module._connection = None


@pytest.fixture
def client(setup_test_db):
    """FastAPI test client with fresh database.

    Clears registered agents so the orchestrator uses stubs (no real LLM calls).
    """
    from app.main import app
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        # Clear registered agents so pipeline uses stubs
        from app.services.pipeline.orchestrator import orchestrator
        orchestrator._agents.clear()
        yield c
