import logging
from dataclasses import asdict

from jobs import Image, Job
from jobs.types import K8sResourceKind
from kubernetes import client

from jobs_server.models import ExecutionMode, SubmissionContext, WorkloadIdentifier
from jobs_server.runner.base import Runner, _make_executor_command
from jobs_server.services.k8s import KubernetesService
from jobs_server.utils.k8s import (
    gvk,
    k8s_annotations,
    sanitize_rfc1123_domain_name,
)
from jobs_server.utils.kueue import kueue_scheduling_labels


class KueueRunner(Runner):
    def __init__(self, k8s: KubernetesService, **kwargs: str) -> None:
        super().__init__()

        self._k8s = k8s
        self._queue = kwargs.get("local_queue", "user-queue")

    def _make_job_crd(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> client.V1Job:
        if not job.options:
            raise ValueError("Job options must be specified")

        scheduling_labels = kueue_scheduling_labels(job, self._k8s.namespace)

        metadata = client.V1ObjectMeta(
            generate_name=sanitize_rfc1123_domain_name(job.name),
            labels=scheduling_labels,
            annotations=k8s_annotations(job, context),
        )

        # Job container
        container = client.V1Container(
            image=image.tag,
            image_pull_policy="IfNotPresent",
            name="workload",
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
        # TODO: Set backoff_limit to a lower number than 6 (default)?
        #  alternatively: pod_failure_policy (needs k8s>=1.31.0)
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=client.V1JobSpec(
                parallelism=3,
                # completions=1,
                suspend=True,
                template=template,
            ),
        )

    def run(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> WorkloadIdentifier:
        logging.info(f"Submitting job {job.name} to Kueue")

        k8s_job = self._make_job_crd(job, image, context)
        batch_api = client.BatchV1Api()
        resource: client.V1Job = batch_api.create_namespaced_job(
            self._k8s.namespace, k8s_job
        )

        logging.info(
            f"Submitted job {resource.metadata.name!r} in namespace {resource.metadata.namespace!r} successfully to Kueue."
        )

        return WorkloadIdentifier(
            **asdict(gvk(resource)),
            name=resource.metadata.name,
            namespace=resource.metadata.namespace,
            uid=resource.metadata.uid,
        )


Runner.register_implementation(KueueRunner, ExecutionMode.KUEUE)
