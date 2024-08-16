import uuid

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from jobs import JobOptions
from pytest_mock import MockFixture

from jobs_server.models import CreateJobModel, WorkloadIdentifier
from jobs_server.runner import KueueRunner, RayJobRunner
from jobs_server.runner.base import ExecutionMode, Runner
from jobs_server.runner.docker import DockerRunner


@pytest.mark.parametrize(
    "runner_type, mode, expected_to_fail",
    [
        # Supported modes
        (KueueRunner, ExecutionMode.KUEUE, False),
        (RayJobRunner, ExecutionMode.RAYJOB, False),
        (DockerRunner, ExecutionMode.DOCKER, False),
        # Unsupported modes
        (None, ExecutionMode.LOCAL, True),
        (None, ExecutionMode.RAYCLUSTER, True),
    ],
)
def test_submit_job(
    runner_type: type[Runner] | None,
    mode: ExecutionMode,
    expected_to_fail: bool,
    client: TestClient,
    mocker: MockFixture,
) -> None:
    "Test the job submission endpoint with various execution modes and validate that jobs are submitted through the correct runner type"

    if runner_type is not None:
        job_id = WorkloadIdentifier(
            group="",
            version="v1",
            kind="Job",
            name="test",
            namespace="default",
            uid=str(uuid.uuid4()),
        )
        mock = mocker.patch.object(runner_type, "run", return_value=job_id)

    body = CreateJobModel(
        image_ref="localhost:5000/hello-world-dev:latest",
        name="test-job",
        file="test_example.py",
        mode=mode,
        options=JobOptions(),
    )
    response = client.post("/jobs", json=jsonable_encoder(body))

    if expected_to_fail:
        assert response.is_error
    else:
        mock.assert_called_once()
        assert response.status_code == 200

        response_model = WorkloadIdentifier.model_validate(response.json())
        assert response_model == job_id
