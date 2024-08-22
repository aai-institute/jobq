import logging
from collections.abc import Generator

from kubernetes import client, config

from jobs_server.exceptions import WorkloadNotFound
from jobs_server.models import JobId
from jobs_server.utils.kueue import KueueWorkload


class KubernetesService:
    def __init__(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            logging.warning(
                "Could not load in-cluster config, attempting to load Kubeconfig",
                exc_info=True,
            )
            config.load_kube_config()

        self._core_v1_api = client.CoreV1Api()

    @property
    def namespace(self) -> str:
        _, active_context = config.list_kube_config_contexts()
        current_namespace = active_context["context"].get("namespace")
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
        return self._core_v1_api.read_namespaced_pod_log(
            pod.metadata.name,
            pod.metadata.namespace,
            tail_lines=tail,
        )

    def stream_pod_logs(
        self, pod: client.V1Pod, tail: int = 100
    ) -> Generator[str, None, None]:
        log_stream = self._core_v1_api.read_namespaced_pod_log(
            pod.metadata.name,
            pod.metadata.namespace,
            tail_lines=tail,
            follow=True,
            _preload_content=False,
        )
        yield from log_stream
