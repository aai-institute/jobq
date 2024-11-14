import random
import string

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from jobq_server.db import Project, ProjectPublic


def _random_project() -> Project:
    namespace = "test-" + "".join(random.choices(string.ascii_lowercase, k=6))
    return Project(
        name="test-project",
        namespace=namespace,
        local_queue="local-queue",
        cluster_queue="cluster-queue",
    )


def test_project_create(client: TestClient) -> None:
    p = _random_project()
    response = client.post("/projects", json=jsonable_encoder(p))
    assert response.status_code == 201

    project = ProjectPublic.model_validate_json(response.text)
    assert project.name == p.name
    assert project.description == p.description
    assert project.cluster_queue == p.cluster_queue
    assert project.local_queue == p.local_queue
    assert project.namespace == p.namespace
    assert project.id is not None
