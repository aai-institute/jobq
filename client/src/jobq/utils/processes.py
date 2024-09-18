from __future__ import annotations

import logging
import shlex
import subprocess
import sys
import threading
import time
from collections.abc import Iterable, Mapping
from io import TextIOBase
from typing import TextIO

from jobq.types import AnyPath


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

    logging.debug("Running command: %s", command)
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

    if stdin is not None and process.stdin:
        process.stdin.write(stdin.read())
        process.stdin.close()

    # Capture stdout and stderr
    stdout: list[str] = []
    stderr: list[str] = []
    output: list[str] = []

    def _reader(
        in_stream: TextIO | None,
        out_stream: TextIOBase,
        out_lists: Iterable[list[str]],
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
