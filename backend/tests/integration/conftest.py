import docker
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockFixture

import jobs_server.services.k8s
from jobs_server import app


@pytest.fixture
def client(mocker: MockFixture) -> TestClient:
    # Mock entire Kubernetes and Docker client functionality
    mocker.patch.object(jobs_server.services.k8s.config, "load_incluster_config")
    mocker.patch.object(jobs_server.services.k8s.config, "load_kube_config")
    mocker.patch.object(docker, "from_env")

    return TestClient(app)
