import argparse
from argparse import ArgumentParser
from pprint import pp
from typing import Any

import openapi_client

from .util import with_job_mgmt_api


@with_job_mgmt_api
def status(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    resp = client.status_jobs_uid_status_get(uid=args.uid)
    pp(resp)


def add_parser(subparsers: Any, parent: ArgumentParser) -> None:
    # jobby status, the status querying command
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "status",
        parents=[parent],
        description="Query the status of a previously dispatched job.",
    )

    # unique identifier of the job
    parser.add_argument("uid", metavar="<ID>")
    # TODO: Factor out into command class
    parser.set_defaults(func=status)
