# The `jobq` command line interface

To interact with a set up cluster queue, you (the data scientist) can use the `jobq` CLI.
It provides subcommands for the basic administrative tasks around your compute jobs, like submitting and deleting jobs, listing, and querying job status information.

A prerequisite for using jobq is adding configuration to be able to reach the backend API server talking to the Kubernetes cluster.
Currently, only the server URL is required. You can add it directly under a `tool.jobq` block in your `pyproject.toml` file like so:

```toml
# 
[tool.jobq]
api-base-url = "http://localhost:8000"
```

## Submission and termination of compute jobs

To submit compute jobs to your chosen Kubernetes cluster queue, use the `jobq submit` command.

```shell
$ jobq submit -h
usage: jobq submit [-h] [--api-base-url Url] [--log-level str]
                   [--mode {ExecutionMode.LOCAL,ExecutionMode.DOCKER,ExecutionMode.KUEUE,ExecutionMode.RAYJOB}]
                   entrypoint

Execute a job locally or through a jobq server

positional arguments:
  entrypoint

options:
  -h, --help            show this help message and exit
  --api-base-url Url    Base URL of the jobq API server (required)
  --log-level str       Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
  --mode {ExecutionMode.LOCAL,ExecutionMode.DOCKER,ExecutionMode.KUEUE,ExecutionMode.RAYJOB}
                        Job execution mode
```

Here, `entrypoint` is the Python file containing your job definition. For more information on how to define compute jobs in Python with `jobq`, refer to the starter guide [TODO: referral].

The command also contains a dry-run facility to prototype your script locally, by passing the `--mode=local` switch.
This way, you can test your workflow on your own local machine before rolling it out to your actual cluster.

To stop a previously submitted job, use the `jobq stop` command.


```shell
$ jobq stop -h
usage: jobq stop [-h] [--api-base-url Url] [--log-level str] <ID>

Terminate the execution of a previously submitted job

positional arguments:
  <ID>

options:
  -h, --help          show this help message and exit
  --api-base-url Url  Base URL of the jobq API server (required)
  --log-level str     Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
```

The only required argument is the UID of the job to be terminated.
You can easily obtain said UID by listing all previously submitted jobs via `jobq list`.
In such a listing, the UID of each job appears together with its name in the leftmost name column.

## Listing available jobs

As mentioned, to list all submitted jobs, use the `jobq list` command.

```shell
$ jobq list -h
usage: jobq list [-h] [--api-base-url Url] [--log-level str] [--limit <N>] [--filter <cond>]

List previously submitted jobs

options:
  -h, --help          show this help message and exit
  --api-base-url Url  Base URL of the jobq API server (required)
  --log-level str     Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
  --limit <N>         Limit the listing to only a number of the most recent workloads.
  --filter <cond>     Filter existing workloads by a condition of the form <key>=<value> (e.g. status='succeeded'). Can be supplied
                      multiple times for multiple conditions.
```

The resulting table includes useful information about each job such as name and UID, the cluster queue it was admitted to, its execution status, and flags if something unexpected (e.g. pod failures or preemptions) happened during execution.

## Querying job status and logs

`jobq` contains two commands to obtain metadata and information on submitted jobs.

To query a job's status, use the `jobq status` command.

```shell
$ jobq status -h
usage: jobq status [-h] [--api-base-url Url] [--log-level str] <ID>

Query the status of a previously submitted job

positional arguments:
  <ID>

options:
  -h, --help          show this help message and exit
  --api-base-url Url  Base URL of the jobq API server (required)
  --log-level str     Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
```

Again, the job's unique identifier in the cluster is required.
To obtain a job's identifier, use the `jobq list` command.

To get information about the job execution, or to troubleshoot failing pods, you can access a job's logs with the `jobq logs` command.

```shell
$ jobq logs -h  
usage: jobq logs [-h] [--api-base-url Url] [--log-level str] [-f] [--tail TAIL] <ID>

Get logs for specified job

positional arguments:
  <ID>

options:
  -h, --help          show this help message and exit
  --api-base-url Url  Base URL of the jobq API server (required)
  --log-level str     Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
  -f, --follow        Whether to stream logs
  --tail TAIL         Lines of recent logs to display (default: -1, all lines)
```

You can obtain logs in two different modes, either as an ex-post log dump, or in real time via streaming.
Streaming logs can be useful to follow a job's lifecycle. To stream logs, use the `-f` flag.
This feature behaves almost the same as `kubectl logs -f` does, with a few noteworthy differences:

* The order in which already written logs (i.e., those that were written after the stream was requested) are rendered is likely not the same as for `kubectl logs -f`.
* By default, in a multi-pod scenario, meaning multiple pods belong to a job, all logs are prefixed with the pod name to provide visual distinction. This is equivalent to the `--prefix --all-pods` options in `kubectl logs`.

To limit a log selection to a number of the most recently written logs, give the `--tail` option with the desired number of lines.
