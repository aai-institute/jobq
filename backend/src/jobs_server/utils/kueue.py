from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

from jobs.job import Job
from jobs.utils.helpers import remove_none_values
from kubernetes import client, dynamic
from pydantic import UUID4, BaseModel, ConfigDict, field_validator

from jobs_server.exceptions import WorkloadNotFound
from jobs_server.models import JobId, WorkloadExecutionStatus
from jobs_server.utils.helpers import traverse
from jobs_server.utils.k8s import build_metadata, filter_conditions

if TYPE_CHECKING:
    from jobs_server.dependencies import ManagedWorkload


def assert_kueue_localqueue(namespace: str, name: str) -> bool:
    """Check the existence of a Kueue `LocalQueue` in a namespace."""
    try:
        _ = client.CustomObjectsApi().get_namespaced_custom_object(
            "kueue.x-k8s.io",
            "v1beta1",
            namespace,
            "localqueues",
            name,
        )
        return True
    except client.exceptions.ApiException:
        return False


def assert_kueue_workloadpriorityclass(name: str) -> bool:
    """Check the existence of a Kueue `WorkloadPriorityClass` in the cluster."""
    try:
        _ = client.CustomObjectsApi().get_cluster_custom_object(
            "kueue.x-k8s.io",
            "v1beta1",
            "workloadpriorityclasses",
            name,
        )
        return True
    except client.exceptions.ApiException:
        return False


def kueue_scheduling_labels(job: Job, namespace: str) -> Mapping[str, str]:
    """Determine the Kubernetes labels controlling Kueue features such as queues and priority for a job."""

    if not job.options:
        return {}
    if not (sched_opts := job.options.scheduling):
        return {}

    if queue := sched_opts.queue_name:
        if not assert_kueue_localqueue(namespace, queue):
            raise ValueError(f"Specified Kueue local queue does not exist: {queue!r}")
    if pc := sched_opts.priority_class:
        if not assert_kueue_workloadpriorityclass(pc):
            raise ValueError(
                f"Specified Kueue workload priority class does not exist: {pc!r}"
            )

    return cast(
        Mapping[str, str],
        remove_none_values({
            "kueue.x-k8s.io/queue-name": (
                sched_opts.queue_name if sched_opts else None
            ),
            "kueue.x-k8s.io/priority-class": (
                sched_opts.priority_class if sched_opts else None
            ),
        }),
    )


def workload_by_managed_uid(uid: JobId, namespace: str):
    """Find a Kueue Workload by the UID of its underlying job."""

    api = client.CustomObjectsApi()
    objs = api.list_namespaced_custom_object(
        "kueue.x-k8s.io",
        "v1beta1",
        namespace,
        "workloads",
        label_selector=f"kueue.x-k8s.io/job-uid={uid}",
    ).get("items")

    if not objs:
        raise WorkloadNotFound(uid=uid, namespace=namespace)
    return objs[0]


class WorkloadSpec(BaseModel):
    podSets: list
    queueName: str
    priorityClassName: str
    priority: int
    priorityClassSource: str
    active: bool


class WorkloadAdmission(BaseModel):
    clusterQueue: str
    podSetAssignments: list


class WorkloadStatus(BaseModel):
    conditions: list[dict[str, Any]]
    admission: WorkloadAdmission | None = None
    requeueState: Any | None = None
    reclaimablePods: list | None = None
    admissionChecks: list | None = None


class WorkloadMetadata(BaseModel):
    workload_uid: UUID4
    execution_status: WorkloadExecutionStatus
    spec: WorkloadSpec
    status: WorkloadStatus

    @classmethod
    def from_managed_workload(cls, workload: "ManagedWorkload") -> "WorkloadMetadata":
        if workload.owner_uid is None:
            raise ValueError("Workload has no owner UID")
        return cls(
            workload_uid=workload.owner_uid,
            execution_status=workload.execution_status,
            spec=workload.spec,
            status=workload.status,
        )


class KueueWorkload(BaseModel):
    """Wrapper class for Kueue Workload resources.

    See https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-Workload.
    """

    metadata: client.V1ObjectMeta
    spec: WorkloadSpec
    status: WorkloadStatus

    @field_validator("metadata", mode="before")
    def create_metadata(cls, metadata: client.V1ObjectMeta) -> client.V1ObjectMeta:
        return build_metadata(metadata)

    owner_uid: JobId | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @classmethod
    def for_managed_resource(cls, uid: str, namespace: str):
        workload = workload_by_managed_uid(uid, namespace)
        result = cls.model_validate(workload)

        # speed up subsequent lookups of associated resource by memoizing the managed resource UID
        result.owner_uid = uid

        return result

    @property
    def execution_status(self) -> WorkloadExecutionStatus:
        if filter_conditions(self, reason="Succeeded"):
            return WorkloadExecutionStatus.SUCCEEDED
        elif filter_conditions(self, reason="Failed"):
            return WorkloadExecutionStatus.FAILED
        elif traverse(self, "status.admission", strict=False) is not None:
            return WorkloadExecutionStatus.EXECUTING
        else:
            return WorkloadExecutionStatus.PENDING

    @property
    def managed_resource(self):
        owner_ref: client.V1OwnerReference = self.metadata.owner_references[0]

        dyn = dynamic.DynamicClient(client.ApiClient())
        resource = dyn.resources.get(
            api_version=owner_ref.api_version, kind=owner_ref.kind
        )
        owner = dyn.get(resource, owner_ref.name, self.metadata.namespace)
        return owner

    @property
    def pod(self) -> client.V1Pod:
        api = client.CoreV1Api()

        if self.owner_uid is None:
            self.owner_uid = self.managed_resource.metadata["uid"]
        owner_uid = self.owner_uid
        podlist: client.V1PodList = api.list_pod_for_all_namespaces(
            label_selector=f"controller-uid={owner_uid}"
        )
        pods = podlist.items

        if not pods:
            return None
        if len(pods) > 1:
            raise RuntimeError(
                f"more than one pod associated with workload {owner_uid}"
            )
        return pods[0]
