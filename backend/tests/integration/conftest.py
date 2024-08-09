import pytest
from fastapi.testclient import TestClient

from jobs_server import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
