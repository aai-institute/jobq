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

    def _sanitize_log_kwargs(self, tail: int) -> dict[str, int]:
        return {"tail_lines": tail} if tail != -1 else {}

    def get_pod_logs(self, pod: client.V1Pod, tail: int = -1) -> str:
        try:
            return self._core_v1_api.read_namespaced_pod_log(
                pod.metadata.name,
                pod.metadata.namespace,
                **self._sanitize_log_kwargs(tail),
            )
        except client.ApiException as e:
            if e.status == 400:
                raise PodNotReadyError(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                ) from e
            raise

    def stream_pod_logs(
        self, pod: client.V1Pod, tail: int = -1
    ) -> Generator[str, None, None]:
        try:
            log_stream = self._core_v1_api.read_namespaced_pod_log(
                pod.metadata.name,
                pod.metadata.namespace,
                follow=True,
                _preload_content=False,
                **self._sanitize_log_kwargs(tail),
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

    def list_workloads(self, namespace: str | None = None) -> list[KueueWorkload]:
        api = client.CustomObjectsApi()
        workloads = api.list_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace or self.namespace,
            plural="workloads",
        )
        return [
            KueueWorkload.model_validate(workload)
            for workload in workloads.get("items", [])
        ]
