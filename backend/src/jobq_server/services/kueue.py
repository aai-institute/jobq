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
