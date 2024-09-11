class WorkloadNotFound(Exception):
    """Exception indicating a non-existing Kueue workload"""

    def __init__(
        self,
        message: str = "workload not found",
        uid: str | None = None,
        namespace: str | None = None,
    ):
        super().__init__(message)
        self.uid = uid
        self.namespace = namespace


class PodNotReadyError(Exception):
    """Exception indicating a non-ready pod"""

    def __init__(
        self,
        name: str,
        namespace: str,
    ):
        self.pod_name = name
        self.pod_namespace = namespace
        super().__init__(f"pod not ready: {name!r} in {namespace!r}")
