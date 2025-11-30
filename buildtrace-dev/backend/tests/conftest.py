"""Shared pytest fixtures for backend tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gcp.database.models import Base
from config import config


@pytest.fixture(scope="session")
def engine():
    """Create a single in-memory SQLite engine for all tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """Provide a transactional database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def neutral_config(monkeypatch):
    """Ensure sensitive config-driven keys are blank during tests."""
    monkeypatch.setattr(config, "GEMINI_API_KEY", "", raising=False)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(config, "USE_DATABASE", False, raising=False)
    monkeypatch.setenv("USE_DATABASE", "false")
    monkeypatch.setenv("FAST_TEST_MODE", "1")
    yield
