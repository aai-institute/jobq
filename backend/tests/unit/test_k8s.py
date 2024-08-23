import pytest
from kubernetes import client

from jobs_server.utils.k8s import build_metadata


@pytest.mark.parametrize(
    "data, expected_metadata",
    [
        (
            {
                "name": "test-pod",
                "namespace": "default",
                "labels": {"app": "myapp"},
                "annotations": {"description": "test annotation"},
                "ownerReferences": [
                    {
                        "apiVersion": "v1",
                        "kind": "Pod",
                        "name": "owner-pod",
                        "uid": "12345",
                    }
                ],
                "managedFields": [
                    {"manager": "kubelet", "operation": "Update", "apiVersion": "v1"}
                ],
            },
            client.V1ObjectMeta(
                name="test-pod",
                namespace="default",
                labels={"app": "myapp"},
                annotations={"description": "test annotation"},
                owner_references=[
                    client.V1OwnerReference(
                        api_version="v1", kind="Pod", name="owner-pod", uid="12345"
                    )
                ],
                managed_fields=[
                    client.V1ManagedFieldsEntry(
                        manager="kubelet", operation="Update", api_version="v1"
                    )
                ],
            ),
        ),
        (
            {"name": "another-pod", "namespace": "kube-system"},
            client.V1ObjectMeta(
                name="another-pod",
                namespace="kube-system",
            ),
        ),
        (
            om := client.V1ObjectMeta(
                name="test", namespace="default", labels={"app": "myapp"}
            ),
            om,
        ),
    ],
)
def test_instantiate_metadata(data, expected_metadata):
    result = build_metadata(data)
    assert result == expected_metadata  # V1ObjectMeta.__eq__ does deep comparison
