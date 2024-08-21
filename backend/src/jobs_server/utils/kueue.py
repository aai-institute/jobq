from collections.abc import Mapping
from typing import Any, cast

from jobs.job import Job
from jobs.utils.helpers import remove_none_values
from kubernetes import client
from pydantic import BaseModel, ConfigDict

from jobs_server.exceptions import WorkloadNotFound
from jobs_server.models import JobId, JobStatus
from jobs_server.utils.helpers import traverse
from jobs_server.utils.k8s import filter_conditions


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


class KueueWorkload(BaseModel):
    """Wrapper class for Kueue Workload resources.

    See https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-Workload.
    """

    metadata: dict[str, Any]
    spec: WorkloadSpec
    status: WorkloadStatus

    model_config = ConfigDict(
        arbitrary_types_allowed=False,
    )

    @classmethod
    def for_managed_resource(cls, uid: str, namespace: str):
        workload = workload_by_managed_uid(uid, namespace)
        return cls.model_validate(workload)

    @property
    def execution_status(self) -> JobStatus:
        if filter_conditions(self, reason="Succeeded"):
            return JobStatus.SUCCEEDED
        elif filter_conditions(self, reason="Failed"):
            return JobStatus.FAILED
        elif traverse(self, "status.admission", strict=False) is not None:
            return JobStatus.EXECUTING
        else:
            return JobStatus.PENDING
