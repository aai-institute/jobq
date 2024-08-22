from jobs_server.services.k8s import KubernetesService


def k8s_service() -> KubernetesService:
    return KubernetesService()
