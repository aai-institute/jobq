import logging
import random
import shlex
import string
import sys
import time
from pathlib import Path
from typing import AbstractSet

import yaml
from kubernetes import client
from ray.dashboard.modules.job.common import JobStatus
from ray.dashboard.modules.job.sdk import JobSubmissionClient

import jobs
from jobs import Image, Job
from jobs.job import RayResourceOptions
from jobs.runner.base import Runner, _make_executor_command
from jobs.types import K8sResourceKind, NoOptions
from jobs.util import KubernetesNamespaceMixin, sanitize_rfc1123_domain_name
from jobs.utils.kueue import kueue_scheduling_labels


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
        status_to_wait_for: AbstractSet[JobStatus] = frozenset(
            {JobStatus.SUCCEEDED, JobStatus.STOPPED, JobStatus.FAILED}
        ),
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

    def run(self, job: Job, image: Image) -> None:
        head_url = self._head_url
        logging.info(f"Submitting job {job.name} to Ray cluster at {head_url!r}")

        ray_jobs = JobSubmissionClient(head_url)
        ray_options: RayResourceOptions | NoOptions = (
            res.to_ray()
            if job.options and (res := job.options.resources)
            else NoOptions()
        )

        # TODO: Lots of hardcoded stuff here
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


class RayJobRunner(Runner, KubernetesNamespaceMixin):
    """Job runner that submits ``RayJob`` resources to a Kubernetes cluster running the Kuberay operator."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _create_ray_job(self, job: Job, image: Image) -> dict:
        """Create a ``RayJob`` Kubernetes resource for the Kuberay operator."""

        if job.options is None:
            raise ValueError("Job options must be set")

        res_opts = job.options.resources
        if not res_opts:
            raise ValueError("Job resource options must be set")

        scheduling_labels = kueue_scheduling_labels(job, self.namespace)

        runtime_env = {
            "working_dir": "/home/ray/app",
        }

        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        job_id = f"{job.name}-{suffix}"
        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayJob",
            "metadata": {
                "name": sanitize_rfc1123_domain_name(job_id),
                "labels": scheduling_labels,
            },
            "spec": {
                "jobId": job_id,
                "entrypoint": shlex.join(_make_executor_command(job)),
                "runtimeEnvYAML": yaml.dump(runtime_env),
                "shutdownAfterJobFinishes": True,
                "rayClusterSpec": {
                    "rayVersion": "2.10.0",  # TODO: Automatically determine Ray version from environment
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
                                        "imagePullPolicy": "Always",
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
            },
        }

        return manifest

    def run(self, job: Job, image: Image) -> None:
        logging.info(f"Submitting RayJob {job.name} to namespace {self.namespace!r}")

        manifest = self._create_ray_job(job, image)
        api = client.CustomObjectsApi()
        res = api.create_namespaced_custom_object(
            "ray.io", "v1", self.namespace, "rayjobs", manifest
        )
