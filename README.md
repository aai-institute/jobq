# jobq: Packaging, scheduling, and monitoring Python workloads as k8s jobs

jobq is a tool to define, schedule, and observe compute jobs as Python functions in Kubernetes.
It supports Docker (standard Kubernetes), Kueue, and Ray backends for workload execution.

The `jobq` Python package itself is split into a client and backend part.
The client package is used to define jobs with the `@job` decorator in your Python files, and (optionally) to interact with an existing API server through a CLI.
The backend contains a FastAPI-based server application that acts as an intermediary between the user and the target Kubernetes cluster, and can be easily packaged into a Docker container or a virtual machine for deployment.

## Installation

Depending on what your role is, you will likely require only some parts of the `jobq` package.

As a data scientist, you only require the client part to define and dispatch jobs.
To install the client package, simply use `pip`:

```shell
pip install --upgrade "aai-jobq[cli]"
```

This instruction includes the command-line interface to interact with an existing Kubernetes cluster.
If that functionality is not needed, simply omit the bracketed extra from the install command.
If you need to deploy the backend as well, you will need to install the `jobq-server` package:

```shell
pip install --upgrade aai-jobq-server
```

Define jobs in your `.py` files by using the `@job` decorator on the function that contains your compute logic.
Within the decorator you define the desired resources and link the environment configuration. We support Dockerfiles or a declarative `.yaml` file specification.
Using the `jobq` CLI you can execute jobs locally or submit them to one of the supported backends. 
Additionally, you can query for a job status and fetch logs.

Jobq is an early stage project, so expect rough edges. We are happy for feedback and may accomodate your feature requests, so don't hesitate to get in touch.
