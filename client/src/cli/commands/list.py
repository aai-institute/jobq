import argparse
import operator
from datetime import datetime, timezone
from typing import Any

from humanize import naturaltime, precisedelta
from rich import box
from rich.console import Console
from rich.table import Table

import openapi_client
from cli.types import Settings
from cli.util import with_job_mgmt_api
from openapi_client.models import JobStatus


@with_job_mgmt_api
def list_workloads(
    client: openapi_client.JobManagementApi,
    args: argparse.Namespace,
    settings: Settings,
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
        # if the job is already failed, we don't really need to warn anymore.
        elif wl.has_failed_pods and wl.execution_status != JobStatus.FAILED:
            return "[bright_red] [!][/]"
        else:
            return ""

    resp = client.list_jobs_jobs_get(include_metadata=True)

    t = Table(box=box.MINIMAL, show_lines=True, pad_edge=False)
    t.add_column("Name", min_width=36)  # accommodate for the workload UUID
    t.add_column("Type")
    t.add_column("Status")
    t.add_column("Queue name")
    t.add_column("Priority")
    t.add_column("Submitted")
    t.add_column("Execution time")
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    for wl in sorted(
        resp, key=operator.attrgetter("metadata.submission_timestamp"), reverse=True
    ):
        meta = wl.metadata
        cluster_queue = (
            meta.kueue_status.admission.cluster_queue
            if meta.kueue_status and meta.kueue_status.admission
            else None
        )
        t.add_row(
            f"{wl.name}{status_flags(meta)}\n[bright_black]{wl.id.uid}[/]",
            f"[bright_black]{wl.id.group}/{wl.id.version}/[/]{wl.id.kind}",
            f"{format_status(meta.execution_status)}",
            f"{meta.spec.queue_name}\n[bright_black]↳ {cluster_queue}[/]",
            f"{meta.spec.priority_class_name or '[bright_black]None[/]'}",
            f"{naturaltime(meta.submission_timestamp)}",
            f"{precisedelta((meta.termination_timestamp or now) - meta.last_admission_timestamp) if meta.last_admission_timestamp else '---'}",
        )
    Console().print(t)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobq list, the workload listing command
    help = "List previously submitted jobs"
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "list",
        parents=[parent],
        help=help,
        description=help,
    )

    parser.add_argument(
        "--limit",
        metavar="<N>",
        default=None,
        help="Limit the listing to only a number of the most recent workloads.",
    )

    # TODO: This is not yet implemented
    parser.add_argument(
        "--filter",
        metavar="<cond>",
        action="append",
        help="Filter existing workloads by a condition of the form <key>=<value> "
        "(e.g. status='succeeded'). Can be supplied multiple times for multiple "
        "conditions.",
    )
    parser.set_defaults(func=list_workloads)
