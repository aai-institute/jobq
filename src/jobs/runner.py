import abc
import logging

import docker
from kubernetes import client, config

from jobs import Image, Job

JOBS_EXECUTE_CMD = "jobs_execute"


def _make_command(job: Job) -> list[str]:
    return [
        JOBS_EXECUTE_CMD,
        job._file,
        job._name,
    ]


class Runner(abc.ABC):
    @abc.abstractmethod
    def run(self, job: Job, image: Image) -> None: ...


class DockerRunner(Runner):
    def run(self, job: Job, image: Image) -> None:
        command = _make_command(job)

        client = docker.from_env()
        client.containers.run(
            image=image.tag,
            command=command,
        )


class KueueRunner(Runner):
    def __init__(self, **kwargs: str) -> None:
        self._namespace = kwargs.get("namespace")
        self._queue = kwargs.get("local_queue", "user-queue")

    def _make_job_crd(self, job: Job, image: Image) -> client.V1Job:
        # FIXME: Name needs to be RFC1123-compliant, add validation/sanitation
        metadata = client.V1ObjectMeta(
            generate_name=job._name,
            labels={
                "kueue.x-k8s.io/queue-name": self._queue,
            },
        )

        # Job container
        container = client.V1Container(
            image=image.tag,
            image_pull_policy="IfNotPresent",
            name="dummy-job",
            command=_make_command(job),
            resources={
                "requests": {
                    "cpu": 1,
                    "memory": "200Mi",
                }
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
        logging.info(f"Submitting job {job._name} to Kueue")

        config.load_kube_config()
        config_cxts = config.list_kube_config_contexts()
        current_namespace = config_cxts[1]["context"]["namespace"]
        k8s_job = self._make_job_crd(job, image)
        batch_api = client.BatchV1Api()

        namespace = self._namespace or current_namespace
        batch_api.create_namespaced_job(namespace, k8s_job)
        logging.info("Submitted job successfully to Kueue.")
