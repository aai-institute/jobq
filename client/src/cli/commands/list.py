import argparse
import operator
from datetime import datetime, timezone
from typing import Any

from humanize import naturaltime, precisedelta
from rich import box
from rich.console import Console
from rich.table import Table

import openapi_client
from openapi_client.models import JobStatus

from .util import with_job_mgmt_api


@with_job_mgmt_api
def list_workloads(
    client: openapi_client.JobManagementApi, args: argparse.Namespace
) -> None:
    def format_status(s: JobStatus) -> str:
        match s:
            case JobStatus.SUCCEEDED:
                return "[bright_green]" + s.value + "[/]"
            case JobStatus.FAILED:
                return "[bright_red bold]" + s.value + "[/]"
            case _:
                return s.value

    def status_flags(wl: openapi_client.WorkloadMetadata) -> str:
        if wl.was_evicted or wl.was_inadmissible:
            return "[bright_yellow] [!][/]"
        else:
            return ""

    resp = client.list_jobs_jobs_get(include_metadata=True)

    t = Table(box=box.MINIMAL, show_lines=True, pad_edge=False)
    t.add_column("Name", min_width=36)  # accommodate for the workload UUID
    t.add_column("Type")
    t.add_column("Status")
    t.add_column("Priority")
    t.add_column("Time since submission")
    t.add_column("Execution Time")
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    for wl in sorted(
        resp, key=operator.attrgetter("metadata.submission_timestamp"), reverse=True
    ):
        meta = wl.metadata
        t.add_row(
            f"{wl.name}\n[bright_black]{wl.id.uid}[/]",
            f"[bright_black]{wl.id.group}/{wl.id.version}/[/]{wl.id.kind}",
            f"{format_status(meta.execution_status)}{status_flags(meta)}",
            f"{wl.metadata.spec.priority_class_name or '[bright_black]None[/]'}",
            f"{naturaltime(meta.submission_timestamp)}",
            f"{precisedelta((meta.termination_timestamp or now) - meta.last_admission_timestamp) if meta.last_admission_timestamp else '---'}",
        )
    Console().print(t)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby status, the status querying command
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "list",
        parents=[parent],
        description="List all previously dispatched jobs.",
    )

    # unique identifier of the job
    parser.add_argument(
        "--limit",
        metavar="<N>",
        default=None,
        help="Limit the listing to only a number of the most recent workloads.",
    )
    parser.add_argument(
        "--filter",
        metavar="<cond>",
        action="append",
        help="Filter existing workloads by a condition of the form <key>=<value> "
        "(e.g. status='succeeded'). Can be supplied multiple times for multiple "
        "conditions.",
    )
    parser.set_defaults(func=list_workloads)
