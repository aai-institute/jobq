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
