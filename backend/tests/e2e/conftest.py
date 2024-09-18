import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from kubernetes import config
from testcontainers.core.image import DockerImage

from jobq_server import app

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


def setup_kuberay(cluster: KubernetesCluster, kuberay_version: str = "1.1.0"):
    # Install KubeRay Helm chart
    cluster.helm(
        "repo", "add", "kuberay", "https://ray-project.github.io/kuberay-helm/"
    )
    cluster.helm("repo", "update")
    # Check if the operator is already installed

    release_name = "kuberay-operator"
    try:
        cluster.helm("get", "values", release_name)
    except subprocess.CalledProcessError:
        # Install the operator
        cluster.helm(
            "install",
            release_name,
            "kuberay/kuberay-operator",
            "--version",
            kuberay_version,
            "--wait",
        )


@pytest.fixture(scope="session")
def cluster() -> Generator[KubernetesCluster, None, None]:
    """Create a Kubernetes cluster for testing based on environment variable"""
    cluster_type = os.getenv("E2E_CLUSTER_TYPE", "minikube").lower()
    context = os.getenv("E2E_K8S_CONTEXT")
    if cluster_type == "minikube":
        cluster = MinikubeCluster(name=context)
    else:
        cluster = KindCluster(name=context)

    try:
        # Install Kuberay first, so that the CRDs (RayJob, RayCluster)
        # are available for Kueue to be watched.
        setup_kuberay(cluster)
        setup_kueue(cluster)
        yield cluster
    finally:
        cluster.delete()


@pytest.fixture(scope="session")
def mock_kube_config(cluster: KubernetesCluster):
    def mock_load_kube_config(*args, **kwargs):
        return config.load_kube_config(context=cluster.context)

    # need to use raw unittest.mock, since the pytest-mock fixture does not support session scope
    with mock.patch.object(config, "load_config", mock_load_kube_config):
        yield


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
