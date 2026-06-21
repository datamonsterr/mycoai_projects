from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.database import get_db


@pytest.fixture(scope="function")
def client(test_session_factory):
    app = create_app()
    app.dependency_overrides[get_db] = test_session_factory
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
