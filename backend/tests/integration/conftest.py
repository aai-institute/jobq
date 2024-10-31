import docker
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockFixture
from sqlmodel import Session

import jobq_server.db
import jobq_server.services.k8s
from jobq_server import app
from jobq_server.config import settings
from jobq_server.db import get_engine, upgrade_migrations


@pytest.fixture
def client(mocker: MockFixture) -> TestClient:
    # Mock entire Kubernetes and Docker client functionality
    mocker.patch.object(jobq_server.services.k8s.config, "load_config")
    mocker.patch.object(jobq_server.services.k8s.config, "load_incluster_config")
    mocker.patch.object(jobq_server.services.k8s.config, "load_kube_config")
    mocker.patch.object(docker, "from_env")

    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def db():
    # Use a SQLite in-memory database for testing
    settings.DB_CONNECTION_STRING = "sqlite:///:memory:"
    settings.AUTO_MIGRATE = True

    upgrade_migrations()
    with Session(get_engine()) as session:
        yield session
