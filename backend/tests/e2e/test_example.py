from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from jobs import JobOptions, SchedulingOptions

from jobs_server.models import CreateJobModel, WorkloadIdentifier


def test_create_job(client: TestClient):
    body = CreateJobModel(
        image_ref="alpine:latest",  # FIXME: Provide proper e2e test image
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
    assert response.json() == "pending"

    # Check workload logs
    response = client.get(f"/jobs/{workload_id.uid}/logs")
    assert response.status_code == 200
