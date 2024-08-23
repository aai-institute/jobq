import logging
import subprocess
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from kubernetes import config

from jobs_server import app


class KindCluster:
    def __init__(self, name: str | None = None):
        if name is None:
            name = f"integration-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if " " in name:
            raise ValueError(f"invalid cluster name: {name}")

        self.name = name
        self.context = None
        self.kubeconfig = None
        self.create()

    def kubectl(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["kubectl", "--context", self.context, *args],
            check=check,
        )

    def create(self):
        logging.info(f"Creating kind cluster {self.name}")
        subprocess.run(["kind", "create", "cluster", "--name", self.name], check=True)
        self.context = f"kind-{self.name}"
        self.kubeconfig = subprocess.run(
            ["kind", "get", "kubeconfig", "--name", self.name],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

        # Set `default` namespace
        self.kubectl("config", "set-context", self.context, "--namespace", "default")

    def delete(self):
        if self.context:
            logging.info(f"Deleting kind cluster {self.name}")
            subprocess.run(["kind", "delete", "cluster", "--name", self.name])


def setup_kueue(cluster: KindCluster, kueue_version: str = "v0.8.0"):
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


@pytest.fixture(scope="session", autouse=True)
def kind_cluster() -> Generator[KindCluster, None, None]:
    """Create a kind cluster for testing"""
    cluster = KindCluster()
    setup_kueue(cluster)
    try:
        yield cluster
    finally:
        cluster.delete()


@pytest.fixture(autouse=True)
def mock_kube_config(monkeypatch, kind_cluster: KindCluster):
    def mock_load_kube_config(*args, **kwargs):
        return config.load_kube_config(context=kind_cluster.context)

    monkeypatch.setattr(config, "load_config", mock_load_kube_config)


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    return TestClient(app)
