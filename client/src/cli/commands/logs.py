import argparse
from pprint import pp
from typing import Any

import openapi_client

from .util import with_job_mgmt_api


@with_job_mgmt_api
def logs(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    params = {
        k: v
        for k, v in {
            "uid": args.uid,
            "namespace": args.namespace,
            "stream": args.stream,
            "tail": args.tail,
        }.items()
        if v is not None
    }

    resp = client.logs_jobs_uid_logs_get(**params)
    pp(resp)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby logs, command to fetch logs for workload
    parser = subparsers.add_parser("logs", description="Get logs for specified job.")
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace the job was created in, "
        "defaults to currently active namespace.",
    )
    parser.add_argument("uid", metavar="<ID>")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Whether to stream logs",
    )
    parser.add_argument(
        "--tail",
        type=int,
        help="Fetch N most recent log entries",
    )
    parser.set_defaults(func=logs)
