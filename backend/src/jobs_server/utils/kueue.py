from collections.abc import Mapping
from typing import cast

from jobs.job import Job
from jobs.utils.helpers import remove_none_values
from kubernetes import client


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
