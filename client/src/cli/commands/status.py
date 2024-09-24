import argparse
from argparse import ArgumentParser
from typing import Any

import openapi_client
from cli.types import Settings
from cli.util import with_job_mgmt_api
from jobq.utils.helpers import format_dict


@with_job_mgmt_api
def status(
    client: openapi_client.JobManagementApi,
    args: argparse.Namespace,
    settings: Settings,
) -> None:
    resp = client.status_jobs_uid_status_get(uid=args.uid)
    print(format_dict(resp.to_dict()))


def add_parser(subparsers: Any, parent: ArgumentParser) -> None:
    # jobq status, the status querying command
    help = "Query the status of a previously submitted job"
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "status",
        parents=[parent],
        help=help,
        description=help,
    )

    # unique identifier of the job
    parser.add_argument("uid", metavar="<ID>")
    # TODO: Factor out into command class
    parser.set_defaults(func=status)
