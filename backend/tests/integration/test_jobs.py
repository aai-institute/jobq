import uuid

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from jobs import JobOptions
from pytest_mock import MockFixture

import jobs_server
import jobs_server.services
from jobs_server.models import CreateJobModel, WorkloadIdentifier
from jobs_server.runner import KueueRunner, RayJobRunner
from jobs_server.runner.base import ExecutionMode, Runner
from jobs_server.runner.docker import DockerRunner
from jobs_server.services.k8s import KubernetesService


@pytest.fixture(autouse=True)
def mock_kubernetes_config(mocker: MockFixture) -> None:
    mocker.patch.object(jobs_server.services.k8s.config, "load_incluster_config")
    mocker.patch.object(jobs_server.services.k8s.config, "load_kube_config")


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
        assert response.is_success

        response_model = WorkloadIdentifier.model_validate(response.json())
        assert response_model == job_id


class TestJobStatus:
    def test_success(self, client: TestClient, mocker: MockFixture) -> None:
        mock = mocker.patch.object(KubernetesService, "workload_for_managed_resource")

        job_id = uuid.uuid4()
        response = client.get(f"/jobs/{job_id}/status")

        assert response.is_success
        mock.assert_called_once_with(job_id, "default")

    def test_not_found(self, client: TestClient, mocker: MockFixture) -> None:
        mock = mocker.patch.object(
            KubernetesService, "workload_for_managed_resource", return_value=None
        )

        job_id = uuid.uuid4()
        response = client.get(f"/jobs/{job_id}/status")

        assert response.status_code == 404
        mock.assert_called_once_with(job_id, "default")


class TestJobLogs:
    def test_not_found(self, client: TestClient, mocker: MockFixture) -> None:
        mock = mocker.patch.object(
            KubernetesService,
            "workload_for_managed_resource",
            return_value=None,
        )

        job_id = uuid.uuid4()
        response = client.get(f"/jobs/{job_id}/logs")

        assert response.status_code == 404
        mock.assert_called_once()

    def test_tail(self, client: TestClient, mocker: MockFixture) -> None:
        mock = mocker.patch.object(
            KubernetesService,
            "workload_for_managed_resource",
        )
        mock_pod_logs = mocker.patch.object(
            KubernetesService,
            "get_pod_logs",
            side_effect=lambda _, /, tail: "\n" * tail,
        )

        job_id = uuid.uuid4()
        tail_lines = 10

        response = client.get(f"/jobs/{job_id}/logs?stream=false&tail={tail_lines}")

        assert response.is_success
        assert len(str(response.json()).splitlines()) == tail_lines
        mock.assert_called_once()
        mock_pod_logs.assert_called_once()

    def test_stream(self, client: TestClient, mocker: MockFixture) -> None:
        mock = mocker.patch.object(
            KubernetesService,
            "workload_for_managed_resource",
        )
        mock_pod_logs = mocker.patch.object(
            KubernetesService,
            "stream_pod_logs",
            return_value=iter(["line1", "line2"]),
        )

        job_id = uuid.uuid4()
        response = client.get(f"/jobs/{job_id}/logs?stream=true")

        assert response.is_success
        mock.assert_called_once()
        mock_pod_logs.assert_called_once()
