from __future__ import annotations

import re
import shlex
import subprocess
import sys
import threading
import time
from io import TextIOBase
from typing import IO, Any, AnyStr, Iterable, Mapping, TextIO, TypeVar, cast

from jobs.types import AnyPath

T = TypeVar("T", bound=Mapping[str, Any])


def to_rational(s: str) -> float:
    """Convert a number with optional SI/binary unit to floating-point"""

    matches = re.match(r"(?P<magnitude>[+\-]?\d*[.,]?\d+)(?P<suffix>[a-zA-Z]*)", s)
    if not matches:
        raise ValueError(f"Could not parse {s}")
    magnitude = float(matches.group("magnitude"))
    suffix = matches.group("suffix")

    factor = {
        # SI / Metric
        "m": 1e-3,
        "k": 1e3,
        "M": 1e6,
        "G": 1e9,
        "T": 1e12,
        # Binary
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "Ti": 2**40,
        # default
        "": 1.0,
    }.get(suffix)
    if factor is None:
        raise ValueError(f"unknown unit suffix: {suffix}")

    return factor * magnitude


def remove_none_values(d: T) -> T:
    """Remove all keys with a ``None`` value from a dict."""
    filtered_dict = {k: v for k, v in d.items() if v is not None}
    return cast(T, filtered_dict)


def sanitize_rfc1123_domain_name(s: str) -> str:
    """Sanitize a string to be compliant with RFC 1123 domain name

    Note: Any invalid characters are replaced with dashes."""

    # TODO: This is obviously wildly incomplete
    return s.replace("_", "-")


def run_command(
    command: str,
    cwd: AnyPath | None = None,
    verbose: bool = False,
    env: Mapping[str, str] | None = None,
    stdin: TextIO | None = None,
) -> tuple[int, list[str], list[str], list[str]]:
    """Run a command in a subprocess.

    Parameters
    ----------
    command : str
        Command to run
    cwd : os.PathLike[str] | Path | None, optional
        Working directory
    verbose : bool, optional
        Forward command output to stdout/stderr
    env : dict[str, str], optional
        Environment for the new process, by default the current environment
    stdin : BinaryIO | None, optional
        Standard input for the new process, by default `None`

    Returns
    -------
    tuple[int, list[str], list[str], list[str]]
        a tuple containing the return code and the output of the command (stdout, stderr, and combined)
    """

    # No need to split the command string on Windows
    if sys.platform == "win32":
        args = command
    else:
        args = shlex.split(command)

    process = subprocess.Popen(
        args=args,
        stdin=subprocess.PIPE if stdin else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        encoding="utf-8",
    )

    if stdin is not None:
        process.stdin.write(stdin.read())
        process.stdin.close()

    # Capture stdout and stderr
    stdout: list[str] = []
    stderr: list[str] = []
    output: list[str] = []

    def _reader(
        in_stream: IO[AnyStr] | None,
        out_stream: TextIOBase,
        out_lists: Iterable[list[AnyStr]],
    ) -> None:
        if in_stream is None:
            return
        for line in in_stream:
            for out in out_lists:
                out.append(line)

            if verbose:
                out_stream.write(line)
                out_stream.flush()

    read_stdout = threading.Thread(
        target=_reader,
        kwargs={
            "in_stream": process.stdout,
            "out_stream": sys.stdout,
            "out_lists": [stdout, output],
        },
    )
    read_stderr = threading.Thread(
        target=_reader,
        kwargs={
            "in_stream": process.stderr,
            "out_stream": sys.stderr,
            "out_lists": [stderr, output],
        },
    )

    read_stdout.start()
    read_stderr.start()

    # Wait for process to finish
    while process.poll() is None:
        time.sleep(0.1)

    read_stdout.join()
    read_stderr.join()

    return process.returncode, stdout, stderr, output
