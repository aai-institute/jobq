import argparse
from pprint import pp
from typing import Any

import openapi_client

from .util import with_job_mgmt_api


@with_job_mgmt_api
def stop(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    resp = client.stop_workload_jobs_uid_stop_post(uid=args.uid)
    pp(resp)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobq stop, the execution termination command
    parser = subparsers.add_parser(
        "stop",
        parents=[parent],
        description="Terminate the execution of a previously dispatched job.",
    )
    parser.add_argument("uid", metavar="<ID>")
    parser.set_defaults(func=stop)
