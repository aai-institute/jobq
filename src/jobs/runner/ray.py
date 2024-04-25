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
from typing_extensions import deprecated

import jobs
from jobs import Image, Job
from jobs.runner.base import Runner, _make_executor_command
from jobs.util import KubernetesNamespaceMixin


class RayClusterRunner(Runner, KubernetesNamespaceMixin):
    def __init__(self, **kwargs):
        super().__init__()

        self._head_url = kwargs.get("head_url")
        if self._head_url is None:
            raise ValueError("Ray cluster head URL is unset")

    @deprecated("Needs more ideation")
    def _create_ray_cluster(self) -> None:
        """Create a new Ray cluster in Kubernetes using the Kuberay operator."""
        api = client.CustomObjectsApi()

        manifest = (Path(__file__).parents[2] / "raycluster-manifest.yaml").read_text(
            "utf-8"
        )
        body = yaml.safe_load(manifest)
        obj = api.create_namespaced_custom_object(
            "ray.io", "v1", self.namespace, "rayclusters", body
        )

        logging.debug(f"Created Ray cluster {obj.metadata.name}")

    @deprecated("Needs more ideation")
    def _get_cluster(self):
        """Return the head URL of a Ray cluster running in Kubernetes."""
        api = client.CustomObjectsApi()
        status = api.get_namespaced_custom_object_status(
            "ray.io", "v1", self.namespace, "rayclusters", "raycluster-kuberay"
        )
        if status is None:
            return None
        return status

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
        # TODO: This is non-functional - need to consider split between user and IT ops
        # if self._head_url is None:
        #     cluster = self._get_cluster()
        #     if cluster is None:
        #         self._create_ray_cluster()
        #         head_url = ""
        #     else:
        #         head_url = cluster.get("head", {}).get("serviceIP")

        head_url = self._head_url
        logging.info(f"Submitting job {job.name} to Ray cluster at {head_url!r}")

        ray_jobs = JobSubmissionClient(head_url)

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
            **(res.to_ray() if job.options and (res := job.options.resources) else {}),
        )
        logging.info(f"Submitted Ray job with ID {job_id}")

        execution_time, status = self._wait_until_status(
            job_id, ray_jobs, timeout_seconds=0
        )
        logging.info(
            f"Job finished with status {status.value!r} in {execution_time:.1f}s"
        )
