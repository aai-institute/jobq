import time

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from jobs import JobOptions, ResourceOptions, SchedulingOptions
from testcontainers.core.image import DockerImage

from jobs_server.models import (
    CreateJobModel,
    ExecutionMode,
    JobStatus,
    WorkloadIdentifier,
    WorkloadMetadata,
)

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize(
    "mode",
    [
        ExecutionMode.KUEUE,
        ExecutionMode.RAYJOB,
    ],
)
def test_job_lifecycle(
    client: TestClient,
    job_image: DockerImage,
    mode: ExecutionMode,
):
    """Test the lifecycle of a job from creation to termination."""
    body = CreateJobModel(
        image_ref=str(job_image),
        name="test-job",
        file="test_example.py",
        mode=mode.value,
        options=JobOptions(
            scheduling=SchedulingOptions(
                queue_name="user-queue",
            ),
            resources=ResourceOptions(cpu="1", memory="512Mi"),
        ),
    )
    response = client.post("/jobs", json=jsonable_encoder(body))
    managed_resource_id = WorkloadIdentifier.model_validate_json(response.text)

    time.sleep(0.5)

    # Check workload status
    while True:
        response = client.get(f"/jobs/{managed_resource_id.uid}/status")
        assert response.status_code == 200

        status = WorkloadMetadata.model_validate_json(response.text)
        assert str(status.managed_resource_id) == managed_resource_id.uid
        assert status.execution_status != JobStatus.FAILED
        assert status.kueue_status is not None and status.kueue_status.conditions != []

        if status.execution_status != JobStatus.PENDING:
            break

        time.sleep(0.5)

    # Check workload logs (retry if pod is not ready yet)
    while True:
        response = client.get(f"/jobs/{managed_resource_id.uid}/logs")
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            break
        elif response.status_code == 400:
            assert response.json().get("detail") == "pod not ready"
        elif response.status_code == 404:
            assert response.json().get("detail") == "workload pod not found"

    # Terminate the workload
    response = client.post(f"/jobs/{managed_resource_id.uid}/stop")
    assert response.status_code == 200
