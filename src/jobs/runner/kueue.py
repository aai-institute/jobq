import logging

from kubernetes import client

from jobs import Image, Job
from jobs.runner.base import Runner, _make_executor_command
from jobs.types import K8sResourceKind
from jobs.utils.kubernetes import (
    KubernetesNamespaceMixin,
    k8s_annotations,
    sanitize_rfc1123_domain_name,
)
from jobs.utils.kueue import kueue_scheduling_labels


class KueueRunner(Runner, KubernetesNamespaceMixin):
    def __init__(self, **kwargs: str) -> None:
        super().__init__()

        self._queue = kwargs.get("local_queue", "user-queue")

    def _make_job_crd(self, job: Job, image: Image, namespace: str) -> client.V1Job:
        if not job.options:
            raise ValueError("Job options must be specified")

        scheduling_labels = kueue_scheduling_labels(job, self.namespace)
        annotations = k8s_annotations(job)

        metadata = client.V1ObjectMeta(
            annotations=annotations,
            generate_name=sanitize_rfc1123_domain_name(job.name),
            labels=scheduling_labels,
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
                if (res := job.options.resources)
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
