import importlib.metadata
import logging
import random
import shlex
import string
import sys
import time
from collections.abc import Set as AbstractSet
from dataclasses import asdict
from pathlib import Path

import jobs
import yaml
from jobs import Image, Job
from jobs.job import RayResourceOptions
from jobs.types import K8sResourceKind, NoOptions
from kubernetes import client
from ray.dashboard.modules.job.common import JobStatus
from ray.dashboard.modules.job.sdk import JobSubmissionClient

from jobs_server.models import ExecutionMode, SubmissionContext, WorkloadIdentifier
from jobs_server.runner.base import Runner, _make_executor_command
from jobs_server.services.k8s import KubernetesService
from jobs_server.utils.k8s import (
    gvk,
    k8s_annotations,
    sanitize_rfc1123_domain_name,
)
from jobs_server.utils.kueue import kueue_scheduling_labels


class RayClusterRunner(Runner):
    def __init__(self, **kwargs):
        super().__init__()

        self._head_url = kwargs.get("head_url")
        if self._head_url is None:
            raise ValueError("Ray cluster head URL is unset")

    @staticmethod
    def _wait_until_status(
        job_id: str,
        job_client: JobSubmissionClient,
        status_to_wait_for: AbstractSet[JobStatus] = frozenset({
            JobStatus.SUCCEEDED,
            JobStatus.STOPPED,
            JobStatus.FAILED,
        }),
        timeout_seconds: int = 10,
    ) -> tuple[float, JobStatus]:
        """Wait until a Ray Job has entered any of a set of desired states (defaults to all final states)."""

        start = time.time()
        status = job_client.get_job_status(job_id)

        # 0 means no timeout
        if timeout_seconds == 0:
            timeout_seconds = sys.maxsize

        while time.time() - start <= timeout_seconds:
            if status in status_to_wait_for:
                break
            time.sleep(0.5)
            status = job_client.get_job_status(job_id)

        return time.time() - start, status

    def run(self, job: Job, image: Image, context: SubmissionContext) -> None:
        head_url = self._head_url
        logging.info(f"Submitting job {job.name} to Ray cluster at {head_url!r}")

        ray_jobs = JobSubmissionClient(head_url)
        ray_options: RayResourceOptions | NoOptions = (
            res.to_ray()
            if job.options and (res := job.options.resources)
            else NoOptions()
        )

        # TODO: Lots of hardcoded stuff here
        # TODO: Add submission context to job
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        job_id = ray_jobs.submit_job(
            submission_id=f"{job.name}_{suffix}",
            entrypoint=shlex.join(_make_executor_command(job)),
            runtime_env={
                "working_dir": Path(job.file).parent,
                "pip": Path("requirements.txt").read_text("utf-8").splitlines(),
                "py_modules": [jobs],
            },
            **ray_options,
        )
        logging.info(f"Submitted Ray job with ID {job_id}")

        execution_time, status = self._wait_until_status(
            job_id, ray_jobs, timeout_seconds=0
        )
        logging.info(
            f"Job finished with status {status.value!r} in {execution_time:.1f}s"
        )


class RayJobRunner(Runner):
    """Job runner that submits ``RayJob`` resources to a Kubernetes cluster running the Kuberay operator."""

    def __init__(self, k8s: KubernetesService, **kwargs):
        super().__init__(**kwargs)

        self._k8s = k8s

    def _create_ray_job(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> dict:
        """Create a ``RayJob`` Kubernetes resource for the Kuberay operator."""

        if job.options is None:
            raise ValueError("Job options must be set")

        res_opts = job.options.resources
        if not res_opts:
            raise ValueError("Job resource options must be set")

        try:
            ray_version = importlib.metadata.version("ray")
        except importlib.metadata.PackageNotFoundError:
            raise RuntimeError(
                "Could not determine Ray version, is it installed in your environment?"
            ) from None

        scheduling_labels = kueue_scheduling_labels(job, self._k8s.namespace)

        runtime_env = {
            "working_dir": "/home/ray/app",
        }

        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        job_id = f"{job.name}-{suffix}"

        # FIXME: Image pull policy should be configurable
        # It is currently hardcoded to "IfNotPresent" to support running
        # the E2E tests in a cluster without a proper image registry.
        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayJob",
            "metadata": {
                "name": sanitize_rfc1123_domain_name(job_id),
                "labels": scheduling_labels,
                "annotations": k8s_annotations(job, context),
            },
            "spec": {
                "jobId": job_id,
                "suspend": True,
                "entrypoint": shlex.join(_make_executor_command(job)),
                "runtimeEnvYAML": yaml.dump(runtime_env),
                "shutdownAfterJobFinishes": True,
                "rayClusterSpec": {
                    "rayVersion": ray_version,
                    "headGroupSpec": {
                        "rayStartParams": {
                            "dashboard-host": "0.0.0.0",
                            "disable-usage-stats": "true",
                        },
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "head",
                                        "image": image.tag,
                                        "imagePullPolicy": "IfNotPresent",
                                        "resources": {
                                            "requests": res_opts.to_kubernetes(
                                                kind=K8sResourceKind.REQUESTS
                                            ),
                                            "limits": res_opts.to_kubernetes(
                                                kind=K8sResourceKind.LIMITS
                                            ),
                                        },
                                    },
                                ]
                            }
                        },
                    },
                },
                "submitterPodTemplate": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "ray-submit",
                                "image": image.tag,
                                "imagePullPolicy": "IfNotPresent",
                            }
                        ],
                    },
                },
            },
        }

        return manifest

    def run(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> WorkloadIdentifier:
        logging.info(
            f"Submitting RayJob {job.name} to namespace {self._k8s.namespace!r}"
        )

        manifest = self._create_ray_job(job, image, context)
        api = client.CustomObjectsApi()
        obj = api.create_namespaced_custom_object(
            "ray.io", "v1", self._k8s.namespace, "rayjobs", manifest
        )

        return WorkloadIdentifier(
            **asdict(gvk(obj)),
            name=obj["metadata"]["name"],
            namespace=obj["metadata"]["namespace"],
            uid=obj["metadata"]["uid"],
        )


Runner.register_implementation(RayClusterRunner, ExecutionMode.RAYCLUSTER)
Runner.register_implementation(RayJobRunner, ExecutionMode.RAYJOB)
