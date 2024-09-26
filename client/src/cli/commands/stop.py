import argparse
from pprint import pp
from typing import Any

import openapi_client
from cli.types import Settings
from cli.util import with_job_mgmt_api


@with_job_mgmt_api
def stop(
    client: openapi_client.JobManagementApi,
    args: argparse.Namespace,
    settings: Settings,
) -> None:
    resp = client.stop_workload_jobs_uid_stop_post(uid=args.uid)
    pp(resp)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobq stop, the execution termination command
    help = "Terminate the execution of a previously submitted job"
    parser = subparsers.add_parser(
        "stop",
        parents=[parent],
        help=help,
        description=help,
    )
    parser.add_argument("uid", metavar="<ID>")
    parser.set_defaults(func=stop)
