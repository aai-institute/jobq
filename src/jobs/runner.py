import abc
import enum
import logging
import random
import shlex
import string
import sys
import textwrap
import time
from pathlib import Path

import docker
import docker.types
import yaml
from kubernetes import client, config
from ray.job_submission import JobStatus, JobSubmissionClient
from typing_extensions import deprecated

import jobs
from jobs import Image, Job
from jobs.job import DockerResourceOptions
from jobs.types import K8sResourceKind
from jobs.util import remove_none_values, sanitize_rfc1123_domain_name

JOBS_EXECUTE_CMD = "jobs_execute"


def _make_executor_command(job: Job) -> list[str]:
    """Build the command line arguments for running a job locally through the job executor."""
    return [
        JOBS_EXECUTE_CMD,
        job.file,
        job.name,
    ]


class Runner(abc.ABC):
    @abc.abstractmethod
    def run(self, job: Job, image: Image) -> None: ...


class DockerRunner(Runner):
    def __init__(self):
        self._client = docker.from_env()

    def run(self, job: Job, image: Image) -> None:
        command = _make_executor_command(job)

        resource_kwargs: DockerResourceOptions = {
            "mem_limit": None,
            "nano_cpus": None,
            "device_requests": None,
        }
        if job.options and (res := job.options.resources):
            resource_kwargs = res.to_docker()

        container: docker.api.client.ContainerApiMixin = self._client.containers.run(
            image=image.tag,
            command=command,
            detach=True,
            **remove_none_values(resource_kwargs),
        )

        exit_code = container.wait()

        logging.debug(
            f"Container exited with code {exit_code.get('StatusCode')}, output:\n%s",
            textwrap.indent(container.logs().decode(encoding="utf-8"), " " * 4),
        )


class KueueRunner(Runner):
    def __init__(self, **kwargs: str) -> None:
        self._namespace = kwargs.get("namespace")
        self._queue = kwargs.get("local_queue", "user-queue")
        config.load_kube_config()

    def _make_job_crd(self, job: Job, image: Image) -> client.V1Job:
        metadata = client.V1ObjectMeta(
            generate_name=sanitize_rfc1123_domain_name(job.name),
            labels={
                "kueue.x-k8s.io/queue-name": self._queue,
            },
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

        _, active_context = config.list_kube_config_contexts()
        current_namespace = active_context["context"].get("namespace")

        k8s_job = self._make_job_crd(job, image)
        logging.debug(k8s_job)

        batch_api = client.BatchV1Api()

        namespace = self._namespace or current_namespace
        resource: client.V1Job = batch_api.create_namespaced_job(namespace, k8s_job)

        logging.info(
            f"Submitted job {resource.metadata.name!r} in namespace {resource.metadata.namespace!r} successfully to Kueue."
        )


class RayClusterRunner(Runner):
    def __init__(self, **kwargs):
        super().__init__()

        self._head_url = kwargs.get("head_url")
        if self._head_url is None:
            raise ValueError("Ray cluster head URL is unset")

        self._namespace = kwargs.get("namespace")

        config.load_kube_config()

    @property
    def namespace(self) -> str:
        _, active_context = config.list_kube_config_contexts()
        current_namespace = active_context["context"].get("namespace")
        return self._namespace or current_namespace

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
        job_id,
        job_client: JobSubmissionClient,
        status_to_wait_for=frozenset(
            {JobStatus.SUCCEEDED, JobStatus.STOPPED, JobStatus.FAILED}
        ),
        timeout_seconds=10,
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


class ExecutionMode(enum.Enum):
    LOCAL = "local"
    DOCKER = "docker"
    KUEUE = "kueue"
    RAYCLUSTER = "raycluster"
