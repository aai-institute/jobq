# Jobq, workflow submission and scheduling

Jobq is a tool that aims to make it easy for you to create, submit and schedule workflows.

To get teams shipping fast, we keep the definition of the workflows inside a familiar environment: Python.
You wrap all your logic into a function that you then decorate with the `@job` decorator.
In this decorator you will define the environment and hardware requirements.

You then use the `jobq` CLI to submit the workflow, stop it, or retrieve logs.

The `jobq` backed is built on top of Kubernetes and is installed in the cluster, orchestrates the workflow management, and interfaces to the client CLI calls.

Let us walk through an example.
The example expects a set-up cluster and API server.

## Workflow definition in your Python files

To restructure your Python script into a workflow that can be executed by `jobq` you need to reorganize your logic such that everything is called from one top level function.
Then you decorate this function with the `jobq.job` decorator.
The decorator takes two arguments, `image` and `options`.
You use the `image` argument to submit `ImageOptions`, a wrapper specifying the image, that is the environment your code will execute in.
The `ImageOptions` take a `spec`, that is a path to a `.yaml` or `Dockerfile` which outlines the environment creation, as well as the name and tag of the image.

The other argument to the `job` decorator are `options`.
Here you specify the desired resources using the `ResourceOptions` wrapper, can attach labels and specify the `SchedulingOptions`.

A defined job looks similar to this

```python
# quickstart.py
from pathlib import Path
from jobq import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job

@job(
    options=JobOptions(
        labels={"type": "hello-world@quickstart"},
        resources=ResourceOptions(memory='1Gi', cpu='1'),
        scheduling=SchedulingOptions(
            priority_class='background', queue_name="user-queue"
        ),
        image=ImageOptions(
            spec=Path('dockerfile/path/relative/to/job'),
            name="quickstart/hello-world",
            tag="latest"
        )
    )
)
def quickstart():
    print("Hello, World!")
```

## Interface with your workflows using the `jobq` CLI

Now that we have the job defined let us execute it.
You can execute the job via the CLI,`jobq submit quickstart.py`.
This execution is locally, which may be useful for debugging and testing.
However, you probably want to execute the job on the remote cluster.
In this case you can add the `--mode kueue` flag to submit the workflow to the cluster queue (orchestrated by Kubernetes Kueue) like so:
`jobq submit --mode kueue quickstart.py`.

This returns the job id which we can use to fetch or stream the logs using `jobq logs <job id>`.

## Setting up the `jobq` Backend and API server

In this quickstart guide we use Minikube to run a Kubernetes cluster locally.

<!-- FIXME: Add link to deployment guide -->

In case you want to deploy the `jobq` backend on your own cluster, follow the instructions here..

Follow the [ instructions ](https://minikube.sigs.k8s.io/docs/start/) to install Minikube in the Minikube docs. You will also need a container or virtual machine manager like [Docker](https://www.docker.com/get-started/).
Then, open a terminal and start Minikube with `minikube start`.

Next, you need to ensure that the registry add-on is enabled.
Do so by running `minikube addons enable registry`.
The registry is where the cluster saves the job images.
