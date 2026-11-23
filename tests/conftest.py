"""Shared fixtures used by API and packing tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.boxes import BOXES, Box


@pytest.fixture
def client() -> TestClient:
    """Create a client for making requests to the FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def catalogue() -> tuple[Box, ...]:
    """Return the available boxes for packing tests."""
    return tuple(BOXES)


@pytest.fixture
def example_package() -> dict[str, int | float]:
    """Return a valid package payload for API tests."""
    return {"id": 123, "width": 10, "height": 10, "length": 10, "weight": 5}
