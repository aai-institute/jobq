import argparse
from pprint import pp
from typing import Any

import openapi_client
from openapi_client import ApiException

from .util import _make_api_client, handle_api_exception


def stop(args: argparse.Namespace) -> None:
    with _make_api_client() as api:
        client = openapi_client.JobManagementApi(api)
        try:
            resp = client.stop_workload_jobs_uid_stop_post(
                uid=args.uid, namespace=args.namespace
            )
            pp(resp)
        except ApiException as e:
            handle_api_exception(e, "termination")


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby stop, the execution termination command
    parser = subparsers.add_parser(
        "stop", description="Terminate the execution of a previously dispatched job."
    )
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace the job was created in, "
        "defaults to currently active namespace.",
    )
    parser.add_argument("uid", metavar="<ID>")
    parser.set_defaults(func=stop)
