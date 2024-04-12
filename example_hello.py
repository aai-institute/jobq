import logging

from jobs import job
from jobs.cli import submit_job


@job
def hello_world():
    print("Hello, World!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    submit_job(hello_world)
