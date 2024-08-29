import argparse
from argparse import ArgumentParser
from pprint import pp
from typing import Any

import openapi_client
import openapi_client.configuration

from .util import with_job_mgmt_api


@with_job_mgmt_api
def status(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    resp = client.status_jobs_uid_status_get(
        uid=args.uid,
        namespace=args.namespace,
    )
    pp(resp)


def add_parser(subparsers: Any, parent: ArgumentParser) -> None:
    # jobby status, the status querying command
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "status",
        description="Query the status of a previously dispatched job.",
    )

    # unique identifier of the job
    parser.add_argument("uid", metavar="<ID>")
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace the job was created in, "
        "defaults to currently active namespace.",
    )
    # TODO: Factor out into command class
    parser.set_defaults(func=status)
