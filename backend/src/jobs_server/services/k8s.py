import logging
from collections.abc import Generator
from pathlib import Path
from typing import Literal

from kubernetes import client, config, dynamic

from jobs_server.exceptions import PodNotReadyError, WorkloadNotFound
from jobs_server.models import JobId
from jobs_server.utils.helpers import traverse
from jobs_server.utils.k8s import GroupVersionKind
from jobs_server.utils.kueue import KueueWorkload


class KubernetesService:
    def __init__(self):
        try:
            config.load_incluster_config()
            self._in_cluster = True
        except config.ConfigException:
            logging.warning(
                "Could not load in-cluster config, attempting to load Kubeconfig",
            )
            config.load_kube_config()
            self._in_cluster = False

        self._core_v1_api = client.CoreV1Api()
        self._dyn_client = dynamic.DynamicClient(client.ApiClient())

    @property
    def namespace(self) -> str:
        if not self._in_cluster:
            _, active_context = config.list_kube_config_contexts()
            current_namespace = traverse(active_context, "context.namespace")
        else:
            # When running in a cluster, determine the namespace from the mounted service account
            try:
                current_namespace = (
                    Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
                    .read_text()
                    .strip()
                )
            except FileNotFoundError as e:
                raise RuntimeError("Could not determine current namespace") from e
        return current_namespace

    def workload_for_managed_resource(
        self, uid: JobId, namespace: str | None = None
    ) -> KueueWorkload | None:
        try:
            return KueueWorkload.for_managed_resource(
                uid, namespace=namespace or self.namespace
            )
        except WorkloadNotFound:
            return None

    def get_pod_logs(self, pod: client.V1Pod, tail: int = 100) -> str:
        try:
            return self._core_v1_api.read_namespaced_pod_log(
                pod.metadata.name,
                pod.metadata.namespace,
                tail_lines=tail,
            )
        except client.ApiException as e:
            if e.status == 400:
                raise PodNotReadyError(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                ) from e
            raise

    def stream_pod_logs(
        self, pod: client.V1Pod, tail: int = 100
    ) -> Generator[str, None, None]:
        try:
            log_stream = self._core_v1_api.read_namespaced_pod_log(
                pod.metadata.name,
                pod.metadata.namespace,
                tail_lines=tail,
                follow=True,
                _preload_content=False,
            )
            yield from log_stream
        except client.ApiException as e:
            if e.status == 400:
                raise PodNotReadyError(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                ) from e
            raise

    def delete_resource(
        self,
        gvk: GroupVersionKind,
        name: str,
        namespace: str,
        propagation_policy: Literal[
            "Foreground", "Background", "Orphan"
        ] = "Foreground",
    ) -> None:
        dyn = dynamic.DynamicClient(client.ApiClient())

        resource = dyn.resources.get(
            api_version=f"{gvk.group}/{gvk.version}" if gvk.group else gvk.version,
            kind=gvk.kind,
        )

        dyn.delete(
            resource,
            name=name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy=propagation_policy),
        )
