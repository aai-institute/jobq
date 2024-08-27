from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from jobs import JobOptions, SchedulingOptions
from testcontainers.core.image import DockerImage

from jobs_server.models import CreateJobModel, WorkloadIdentifier


def test_create_job(client: TestClient, job_image: DockerImage):
    body = CreateJobModel(
        image_ref=str(job_image),
        name="test-job",
        file="test_example.py",
        mode="kueue",
        options=JobOptions(
            scheduling=SchedulingOptions(
                queue_name="user-queue",
            )
        ),
    )
    response = client.post("/jobs", json=jsonable_encoder(body))
    workload_id = WorkloadIdentifier.model_validate_json(response.text)

    # Check workload status
    response = client.get(f"/jobs/{workload_id.uid}/status")
    assert response.status_code == 200
    assert response.json() in ["pending", "executing"]

    # Check workload logs
    response = client.get(f"/jobs/{workload_id.uid}/logs")
    assert response.status_code == 200
