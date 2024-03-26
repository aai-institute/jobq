import docker

from jobs import Image, Job

JOBS_EXECUTE_CMD = "jobs_execute"


class Runner:
    @staticmethod
    def run(job: Job, image: Image) -> None:
        command = [
            JOBS_EXECUTE_CMD,
            job._file,
            job._name,
        ]

        client = docker.from_env()
        client.containers.run(
            image = image.tag,
            command = command,
        )
