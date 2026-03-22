"""Test fixtures for RAPTOR backend."""

import os
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Set test environment before importing app modules
os.environ["DATABASE_PATH"] = ":memory:"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

from app.core.database import get_db, init_db, _create_connection
import app.core.database as db_module


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create a fresh in-memory database for each test."""
    # Create in-memory connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    # Apply schema
    schema_path = Path(__file__).parent.parent / "app" / "db" / "schema.sql"
    if schema_path.exists():
        conn.executescript(schema_path.read_text())
        conn.commit()

    # Replace the global connection
    db_module._connection = conn

    yield conn

    conn.close()
    db_module._connection = None


@pytest.fixture
def client(setup_test_db):
    """FastAPI test client with fresh database."""
    from app.main import app
    with TestClient(app) as c:
        yield c
