import kubernetes.config
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockFixture

from jobs_server import app


@pytest.fixture
def client(mocker: MockFixture) -> TestClient:
    mocker.patch.object(kubernetes.config, "load_config")
    return TestClient(app)
