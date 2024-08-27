import logging
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime


class KubernetesCluster(ABC):
    def __init__(self, name: str | None = None):
        if name is None:
            name = f"integration-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.context = None
            self._external = False
        else:
            self.context = name
            self._external = True
        if " " in name:
            raise ValueError(f"invalid cluster name: {name}")

        self.name = name
        self.kubeconfig = None

        if not self.context:
            self.create()

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def delete(self):
        pass

    @abstractmethod
    def load_image(self, image: str):
        pass

    def kubectl(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["kubectl", "--context", self.context, *args],
            check=check,
        )


class KindCluster(KubernetesCluster):
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
        if self.context and not self._external:
            logging.info(f"Deleting kind cluster {self.name}")
            subprocess.run(["kind", "delete", "cluster", "--name", self.name])


class MinikubeCluster(KubernetesCluster):
    def create(self):
        logging.info(f"Creating minikube cluster {self.name}")
        subprocess.run([
            "minikube",
            "start",
            "--driver=docker",
            "--cpus=max",
            "--profile",
            self.name,
        ])
        self.context = self.name

    def delete(self):
        if self.context and not self._external:
            logging.info(f"Deleting minikube cluster {self.name}")
            subprocess.run(["minikube", "delete", "--profile", self.name])

    def load_image(self, image: str):
        subprocess.run(
            [
                "minikube",
                "image",
                "load",
                "--daemon=true",
                "--profile",
                self.name,
                image,
            ],
            check=True,
        )
