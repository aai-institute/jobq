import docker
import kubernetes.config
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockFixture

from jobs_server import app


@pytest.fixture
def client(mocker: MockFixture) -> TestClient:
    # Mock entire Kubernetes and Docker client functionality
    mocker.patch.object(kubernetes.config, "load_config")
    mocker.patch.object(docker, "from_env")

    return TestClient(app)
