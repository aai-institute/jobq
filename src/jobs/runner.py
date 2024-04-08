import abc
import logging
import textwrap

import docker
from kubernetes import client, config
from kubernetes.client import V1Job

from jobs import Image, Job

JOBS_EXECUTE_CMD = "jobs_execute"


def _make_container_command(job: Job) -> list[str]:
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
        command = _make_container_command(job)

        resource_kwargs = {}
        if (res := job.options.resources) is not None:
            resource_kwargs = res.to_docker()

        container: docker.api.client.ContainerApiMixin = self._client.containers.run(
            image=image.tag,
            command=command,
            detach=True,
            **resource_kwargs,
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
        # FIXME: Name needs to be RFC1123-compliant, add validation/sanitation
        metadata = client.V1ObjectMeta(
            generate_name=job.name,
            labels={
                "kueue.x-k8s.io/queue-name": self._queue,
            },
        )

        # Job container
        container = client.V1Container(
            image=image.tag,
            image_pull_policy="IfNotPresent",
            name="dummy-job",
            command=_make_container_command(job),
            resources={
                "requests": res.to_kubernetes()
                if (res := job.options.resources)
                else {}
            },
        )

        # Job template
        template = {
            "spec": {
                "containers": [container],
                "restartPolicy": "Never",
            }
        }
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

        logging.info(f"Submitted job {resource.metadata.name!r} in namespace {resource.metadata.namespace!r} successfully to Kueue.")
