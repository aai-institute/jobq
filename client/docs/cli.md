# The `jobq` command line interface

To interact with a set up cluster queue, you (the data scientist) can use the `jobq` CLI.
It provides subcommands for the basic administrative tasks around your compute jobs, like submitting and deleting jobs, listing, and querying job status information.

## Submission and deletion of compute jobs

To submit compute jobs to your chosen Kubernetes cluster queue, use the `jobq submit` command.

```shell
$ jobq submit -h
usage: jobq submit [-h] [-v] [-q] [--image-name IMAGE_NAME]
                   [--mode {ExecutionMode.LOCAL,ExecutionMode.DOCKER,ExecutionMode.KUEUE,ExecutionMode.RAYJOB}]
                   [--kueue-local-queue KUEUE_LOCAL_QUEUE] [--ray-head-url RAY_HEAD_URL]
                   entrypoint

Run an example job either locally, or on a container execution platform

positional arguments:
  entrypoint

options:
  -h, --help            show this help message and exit
  -v                    Enable verbose mode.
  -q                    Enable quiet mode.
  --image-name IMAGE_NAME
                        Image name to use when building a container image
  --mode {ExecutionMode.LOCAL,ExecutionMode.DOCKER,ExecutionMode.KUEUE,ExecutionMode.RAYJOB}
                        Job execution mode
  --kueue-local-queue KUEUE_LOCAL_QUEUE
                        Name of the Kueue LocalQueue to submit the workload to
  --ray-head-url RAY_HEAD_URL
                        URL of the Ray cluster head node
```

Here, `entrypoint` is the Python file containing your job definition. For more information on how to define compute jobs in Python with `jobq`, refer to the starter guide [TODO: referral].

The command also contains a dry-run facility to prototype your script locally, by passing the `--mode=local` switch.
This way, you can test your workflow on your own local machine before rolling it out to your actual cluster.
