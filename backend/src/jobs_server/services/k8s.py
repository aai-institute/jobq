import logging
from collections.abc import Generator
from pathlib import Path

from kubernetes import client, config

from jobs_server.exceptions import PodNotReadyError, WorkloadNotFound
from jobs_server.models import JobId
from jobs_server.utils.helpers import traverse
from jobs_server.utils.kueue import KueueWorkload


class KubernetesService:
    def __init__(self):
        try:
            config.load_incluster_config()
            self._in_cluster = True
        except config.ConfigException:
            logging.warning(
                "Could not load in-cluster config, attempting to load Kubeconfig",
                exc_info=True,
            )
            config.load_kube_config()
            self._in_cluster = False

        self._core_v1_api = client.CoreV1Api()

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

    async def stop_managed_resource(self, resource) -> bool:
        try:
            api_version = resource.apiVersion
            kind = resource.kind
            name = resource.metadata.name
            namespace = resource.metadata.namespace

            resource_api = self._dynamic_client.resources.get(
                api_version=api_version, kind=kind
            )

            await resource_api.delete(name=name, namespace=namespace)

            logging.info(
                f"Successfully terminated managed resource: {kind}/{name} in namespace {namespace}"
            )
            return True
        except Exception as e:
            logging.error(f"Failed to terminate managed resource: {str(e)}")
            return False
