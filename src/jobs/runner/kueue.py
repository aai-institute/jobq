import logging

from kubernetes import client

from jobs import Image, Job
from jobs.runner.base import Runner, _make_executor_command
from jobs.types import K8sResourceKind
from jobs.util import (
    KubernetesNamespaceMixin,
    remove_none_values,
    sanitize_rfc1123_domain_name,
)


class KueueRunner(Runner, KubernetesNamespaceMixin):
    def __init__(self, **kwargs: str) -> None:
        super().__init__()

        self._queue = kwargs.get("local_queue", "user-queue")

    def _make_job_crd(self, job: Job, image: Image, namespace: str) -> client.V1Job:
        def _assert_kueue_localqueue(name: str) -> bool:
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

        def _assert_kueue_workloadpriorityclass(name: str) -> bool:
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

        if not (opts := job.options):
            raise ValueError("No JobOptions for Kueue job found. Did you specify them?")
        else:
            if sched_opts := opts.scheduling:
                if queue := sched_opts.queue_name:
                    if not _assert_kueue_localqueue(queue):
                        raise ValueError(
                            f"Specified Kueue local queue does not exist: {queue!r}"
                        )
                if pc := sched_opts.priority_class:
                    if not _assert_kueue_workloadpriorityclass(pc):
                        raise ValueError(
                            f"Specified Kueue workload priority class does not exist: {pc!r}"
                        )

        metadata = client.V1ObjectMeta(
            generate_name=sanitize_rfc1123_domain_name(job.name),
            labels=remove_none_values(
                {
                    "kueue.x-k8s.io/queue-name": (
                        sched_opts.queue_name
                        if sched_opts and sched_opts.queue_name
                        else self._queue
                    ),
                    "kueue.x-k8s.io/priority-class": (
                        sched_opts.priority_class if sched_opts else None
                    ),
                }
            ),
        )

        # Job container
        container = client.V1Container(
            image=image.tag,
            image_pull_policy="IfNotPresent",
            name="dummy-job",
            command=_make_executor_command(job),
            resources=(
                {
                    "requests": res.to_kubernetes(kind=K8sResourceKind.REQUESTS),
                    "limits": res.to_kubernetes(kind=K8sResourceKind.LIMITS),
                }
                if job.options and (res := job.options.resources)
                else None
            ),
        )

        # Job template
        template = client.V1PodTemplateSpec(
            spec=client.V1PodSpec(containers=[container], restart_policy="Never")
        )
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=client.V1JobSpec(
                parallelism=1,
                completions=1,
                suspend=True,
                template=template,
            ),
        )

    def run(self, job: Job, image: Image) -> None:
        logging.info(f"Submitting job {job.name} to Kueue")

        k8s_job = self._make_job_crd(job, image, self.namespace)
        batch_api = client.BatchV1Api()
        resource: client.V1Job = batch_api.create_namespaced_job(
            self.namespace, k8s_job
        )

        logging.info(
            f"Submitted job {resource.metadata.name!r} in namespace {resource.metadata.namespace!r} successfully to Kueue."
        )
