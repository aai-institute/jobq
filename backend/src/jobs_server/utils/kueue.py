from collections.abc import Mapping
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from jobs.job import Job
from jobs.utils.helpers import remove_none_values
from kubernetes import client, dynamic
from pydantic import UUID4, BaseModel, ConfigDict, field_validator

from jobs_server.exceptions import WorkloadNotFound
from jobs_server.utils.helpers import traverse
from jobs_server.utils.k8s import build_metadata, filter_conditions, gvk

if TYPE_CHECKING:
    from jobs_server.models import JobStatus
    from jobs_server.services.k8s import KubernetesService

JobId = UUID4


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


def workload_by_managed_uid(uid: "JobId", namespace: str):
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
    active: bool
    priorityClassName: str | None = None
    priority: int | None = None
    priorityClassSource: str | None = None


class WorkloadAdmission(BaseModel):
    clusterQueue: str
    podSetAssignments: list


class WorkloadStatus(BaseModel):
    conditions: list[dict[str, Any]]
    admission: WorkloadAdmission | None = None
    requeueState: dict[str, Any] | None = None
    reclaimablePods: list | None = None
    admissionChecks: list | None = None


class KueueWorkload(BaseModel):
    """Wrapper class for Kueue Workload resources.

    See https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-Workload.
    """

    metadata: client.V1ObjectMeta
    spec: WorkloadSpec
    status: WorkloadStatus

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @field_validator("metadata", mode="before")
    def create_metadata(cls, metadata: client.V1ObjectMeta) -> client.V1ObjectMeta:
        return build_metadata(metadata)

    @property
    def owner_uid(self) -> JobId:
        return self.metadata.owner_references[0].uid

    @classmethod
    def for_managed_resource(cls, uid: str, namespace: str):
        workload = workload_by_managed_uid(uid, namespace)
        if workload.get("status") is None:
            raise WorkloadNotFound(uid=uid, namespace=namespace)
        result = cls.model_validate(workload)
        return result

    @property
    def execution_status(self) -> "JobStatus":
        from jobs_server.models import JobStatus

        if filter_conditions(self, reason="Succeeded"):
            return JobStatus.SUCCEEDED
        elif filter_conditions(self, reason="Failed"):
            return JobStatus.FAILED
        elif filter_conditions(self, typ="Admitted", status=True):
            return JobStatus.EXECUTING
        elif filter_conditions(self, typ="QuotaReserved", status=False, reason="Inadmissible"):
            return JobStatus.INADMISSIBLE
        else:
            return JobStatus.PENDING

    @property
    def submission_timestamp(self) -> datetime:
        return self.metadata.creation_timestamp  # type: ignore

    @property
    def last_admission_timestamp(self) -> datetime | None:
        conds = filter_conditions(self, typ="Admitted", status=True)
        return conds[0]["lastTransitionTime"] if conds else None

    @property
    def termination_timestamp(self) -> datetime | None:
        conds = filter_conditions(self, typ="Finished")
        return conds[0]["lastTransitionTime"] if conds else None

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

        if self.managed_resource.kind == "Job":
            # Jobs are simple, they directly control the pods (which we can look up by their controller UID)
            controller_uid = self.owner_uid
        elif self.managed_resource.kind == "RayJob":
            # RayJobs have an additional layer of indirection:
            #
            # The Kuberay operator creates a RayCluster resource for the job,
            # and the pods (head, worker) are in turn created for that RayCluster.
            #
            # Then, a submission job is created to submit the Ray job to the RayCluster.
            # The job is identified by two labels:
            #
            # - `ray.io/originated-from-crd=RayJob`
            # - `ray.io/originated-from-cr-name=<ray-job-name>`
            #
            # Once we know the job, we can find the pods as usual.

            rayjob_name = self.metadata.owner_references[0].name
            submission_jobs: client.BatchV1JobList = client.BatchV1Api().list_namespaced_job(
                namespace=self.metadata.namespace,
                label_selector=f"ray.io/originated-from-crd=RayJob,ray.io/originated-from-cr-name={rayjob_name}",
            )
            submission_jobs = submission_jobs.items

            if not submission_jobs:
                return None
            if len(submission_jobs) > 1:
                raise RuntimeError(
                    f"more than one submission job found for RayJob {rayjob_name!r}: {submission_jobs!r}"
                )

            controller_uid = traverse(submission_jobs[0], "metadata.uid")
        else:
            raise ValueError(f"Unsupported resource kind: {self.managed_resource.kind}")

        podlist: client.V1PodList = api.list_namespaced_pod(
            namespace=self.metadata.namespace,
            label_selector=f"controller-uid={controller_uid}",
        )
        pods = podlist.items
        if not pods:
            return None
        if len(pods) > 1:
            raise RuntimeError(
                f"more than one pod associated with workload {self.metadata.name!r}"
            )
        return pods[0]

    def stop(self, k8s: "KubernetesService") -> None:
        if not self.managed_resource:
            raise RuntimeError(
                f"No managed resource found for workload {self.metadata.name!r}"
            )
        k8s.delete_resource(
            gvk(self.managed_resource.to_dict()),
            self.managed_resource.metadata.name,
            self.managed_resource.metadata.namespace,
        )
