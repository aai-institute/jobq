from time import sleep

from kubernetes import client

from jobq_server.services.k8s import KubernetesService
from jobq_server.utils.kueue import ClusterQueue, LocalQueue


class KueueService:
    def __init__(self, k8s: KubernetesService):
        self.k8s = k8s
        self.custom_obj_api = client.CustomObjectsApi()

    def get_cluster_queue(self, name: str) -> ClusterQueue | None:
        """Get a cluster queue by name.

        Returns
        -------
        ClusterQueue | None
            The cluster queue if it exists, otherwise None.
        """
        try:
            k8s_obj = self.custom_obj_api.get_cluster_custom_object(
                "kueue.x-k8s.io",
                "v1beta1",
                "clusterqueues",
                name,
            )
            return ClusterQueue.model_validate(k8s_obj)
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    def get_local_queue(self, name: str, namespace: str) -> LocalQueue | None:
        """Get a local queue by name and namespace.

        Returns
        -------
        LocalQueue | None
            The local queue if it exists, otherwise None.
        """
        try:
            k8s_obj = self.custom_obj_api.get_namespaced_custom_object(
                "kueue.x-k8s.io",
                "v1beta1",
                namespace,
                "localqueues",
                name,
            )
            return LocalQueue.model_validate(k8s_obj)
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    def create_local_queue(self, queue: LocalQueue) -> None:
        _ = self.k8s.ensure_namespace(queue.metadata.namespace)

        data = {
            "apiVersion": "kueue.x-k8s.io/v1beta1",
            "kind": "LocalQueue",
            **queue.model_dump(),
        }
        return self.custom_obj_api.create_namespaced_custom_object(
            "kueue.x-k8s.io",
            "v1beta1",
            queue.metadata.namespace,
            "localqueues",
            body=data,
        )

    def ensure_local_queue(
        self, name: str, namespace: str, cluster_queue: str | None = None
    ) -> tuple[LocalQueue, bool]:
        if (local_queue := self.get_local_queue(name, namespace)) is not None:
            return local_queue, False

        if cluster_queue is None:
            raise ValueError("Need cluster queue to create new local queue")

        local_queue = LocalQueue(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec={"clusterQueue": cluster_queue},
        )
        self.create_local_queue(local_queue)

        max_retries, base_delay = 5, 0.1
        for attempt in range(max_retries):
            if (created_queue := self.get_local_queue(name, namespace)) is not None:
                return created_queue, True
            sleep(base_delay * (2**attempt))
        raise TimeoutError(f"LocalQueue {name} not created after {max_retries} retries")

    def create_cluster_queue(self, queue: ClusterQueue) -> None:
        data = {
            "apiVersion": "kueue.x-k8s.io/v1beta1",
            "kind": "ClusterQueue",
            **queue.model_dump(),
        }
        return self.custom_obj_api.create_cluster_custom_object(
            "kueue.x-k8s.io",
            "v1beta1",
            "clusterqueues",
            body=data,
        )
