import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from kubernetes import config
from testcontainers.core.image import DockerImage

from jobs_server import app

from .clusters import KindCluster, KubernetesCluster, MinikubeCluster


def setup_kueue(cluster: KubernetesCluster, kueue_version: str = "v0.8.0"):
    # Install Kueue
    cluster.kubectl(
        "apply",
        "--server-side",
        "-f",
        f"https://github.com/kubernetes-sigs/kueue/releases/download/{kueue_version}/manifests.yaml",
    )

    # Wait for Kueue to become ready
    cluster.kubectl(
        "rollout",
        "status",
        "--timeout=60s",
        "-n",
        "kueue-system",
        "deployment/kueue-controller-manager",
    )

    # Apply resources from `resources` directory
    for resource in Path(__file__).parent.joinpath("resources").glob("*.yaml"):
        cluster.kubectl("apply", "--server-side", "-f", str(resource))


@pytest.fixture(scope="session")
def kind_cluster() -> Generator[KindCluster, None, None]:
    """Create a kind cluster for testing"""
    cluster = KindCluster()
    try:
        setup_kueue(cluster)
        yield cluster
    finally:
        cluster.delete()


@pytest.fixture(scope="session")
def minikube_cluster() -> Generator[MinikubeCluster, None, None]:
    """Create a Minikube cluster for testing"""

    context = os.getenv("E2E_K8S_CONTEXT")
    cluster = MinikubeCluster(name=context)
    try:
        setup_kueue(cluster)
        yield cluster
    finally:
        cluster.delete()


@pytest.fixture(scope="session")
def cluster(
    minikube_cluster: MinikubeCluster,
) -> Generator[KubernetesCluster, None, None]:
    yield minikube_cluster


@pytest.fixture(autouse=True)
def mock_kube_config(monkeypatch, cluster: KubernetesCluster):
    def mock_load_kube_config(*args, **kwargs):
        return config.load_kube_config(context=cluster.context)

    monkeypatch.setattr(config, "load_config", mock_load_kube_config)


@pytest.fixture(scope="session")
def job_image(cluster: KubernetesCluster) -> Generator[DockerImage, None, None]:
    with DockerImage(
        path=Path(__file__).parent.joinpath("resources", "job-image"),
        tag="job-image:latest",
    ) as img:
        cluster.load_image(str(img))
        yield img


@pytest.fixture(scope="session")
def client(cluster: KubernetesCluster) -> Generator[TestClient, None, None]:
    return TestClient(app)
