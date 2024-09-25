# Contributing to jobq

Thank you for your interest in contributing to this project!

We appreciate issue reports, pull requests for code and documentation,
as well as any project-related communication through [GitHub Discussions](https://github.com/aai-institute/jobq/discussions).

## Prerequisites

We use the following development tools for all Python code:

-   [uv](https://docs.astral.sh/uv/)
-   [pre-commit](https://pre-commit.com/)
-   [ruff](https://github.com/charliermarsh/ruff) (also part of the `pre-commit` hooks)
-   [pytest](https://docs.pytest.org/en/)

The development version of Python is 3.12, so please make sure to use that version when developing.
The client-side code is tested against Python 3.10 and 3.11, server-side code is tested against Python 3.11, please take this into account when using recent Python features.

To get started with development, [create a fork](https://github.com/aai-institute/jobq/fork) of the GitHub repository and clone it to your local machine.
Please submit your changes as pull requests against the `main` branch.

## Working on the client-side code (decorators & CLI)

The `client/` directory contains the source code for the `jobq` CLI and Python decorators.

### Development

If you want to contribute to the client-side code, you can follow these steps:

1. Create a virtual environment and install the development dependencies:

    ```shell
    cd jobq/client
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements-dev.txt
    uv pip install -e . --no-deps
    ```

2. To run the Pytest test suite, run:

    ```shell
    pytest
    ```

3. After making your changes, verify they adhere to our Python code style by running `pre-commit`:

    ```shell
    pre-commit run --all-files
    ```

    You can also set up Git hooks through `pre-commit` to perform these checks automatically:

    ```shell
    pre-commit install
    ```

### Regenerating the API client

The `src/openapi_client` folder contains an automatically-generated API client for the backend API.

If you make changes to the backend API, you can regenerate the API client with the following command:

```console
hack/openapi-regen.sh
```

This will regenerate the API client in the `client/src/openapi_client` directory from a currently running FastAPI server using [`openapi-generator-cli`](https://openapi-generator.tech/).
Note that you will need to have the backend server running and accessible at `http://localhost:8000` in order to generate the client code.

The script automatically removes unnecessary files and reformats the generated code according to our code style.

### Publishing to PyPI

The `jobq` package is published to [PyPI](https://pypi.org/project/jobq/) through a GitHub Actions workflow when a new release is created.

## Working on the server-side code (API)

The server-side code under the `backend/` folder is written in Python and uses the [FastAPI](https://fastapi.tiangolo.com/) framework.

You can follow the same instructions as for the client-side code to set up a development environment.

### Running the server

Since the code can load Kubernetes credentials from an in-cluster Kubernetes service account or from a Kubeconfig file, you can run it locally without having to deploy to a Kubernetes cluster.

To run the server locally in development mode (accessible at <http://localhost:8000>), you can use the following command in the `backend/` folder:

```console
fastapi dev src/jobq_server
```

FastAPI will automatically reload the server when you make changes to the code.

### Testing

Tests are written wity pytest and can be run with the following command:

```console
pytest
```

The end-to-end tests (under `tests/e2e`) deploy a short-lived Kubernetes cluster and run the tests against those.
You will need to have a few tools installed so the test harness can spin up a Kubernetes cluster:

-   [Docker](https://docs.docker.com/get-docker/) (or another Docker-compatible container runtime like `colima`)
-   [Minikube](https://minikube.sigs.k8s.io/docs/start/)
-   [`kubectl`](https://kubernetes.io/docs/tasks/tools/)
-   [Helm](https://helm.sh/)

After the tests have been run, the cluster will be torn down (also if the test fails).
If you manually abort a test run (which prevents the automatic deletion), you can use `minikube profile list` to find the name of the cluster (`integration-test-<timestamp>`) and then call `minikube delete -p <profile-name>` to delete the cluster.

If you want to run the tests against an existing cluster (which greatly speeds things up), you can provide the name of the context to use through the `E2E_K8S_CONTEXT` environment variable:

```console
E2E_K8S_CONTEXT=minikube pytest
```

> [!WARNING]
> Running the e2e tests against an existing will clutter the active namespace, please proceed with caution!
>
> The test harness attempts to install Kueue and the Kuberay operator into the cluster, so you might run into conflicts if you already have them deployed.

If you want to skip the end-to-end tests (e.g., to speed up the test execution), you can use the following command:

```console
pytest -m "not e2e"
```

### Publishing Docker images

Docker images are published to [GitHub Container Registry](https://github.com/aai-institute/jobq/pkgs/container/jobq-server) through GitHub Actions.

Images are tagged according to the following patterns:

-   `<version>` for release versions
-   `pr-<pr_number>` for pull requests
-   `main` for the `main` branch
-   `<branch_name>` for other branches

The CI workflow also attaches build attestations to the images, which can be used to verify the integrity of the images.

## Updating dependencies

Dependencies should stay locked for as long as possible, ideally for a whole release.
If you have to update a dependency during development, you should do the following:

1. If it is a core dependency needed for the package, add it to the `dependencies` section in the `pyproject.toml`.
2. In case of a development dependency, add it to the `dev` section of the `project.optional-dependencies` table instead.
3. Dependencies needed for documentation generation are found in the `docs` sections of `project.optional-dependencies`.

After adding the dependency in either of these sections, run the helper script `hack/lock-deps.sh` (which in turn uses `uv pip compile`) to pin all dependencies again:

```console
hack/lock-deps.sh
```

In addition to these manual steps, we also provide `pre-commit` hooks that automatically lock the dependencies whenever `pyproject.toml` is changed.

Selective package upgrade for existing dependencies are also handled by the helper script above.
If you want to update the Pydantic dependency, for example, simply run:

```console
hack/lock-deps.sh pydantic
```

> [!IMPORTANT]
> Since the official development version is Python 3.12, please run the above commands in a virtual environment with Python 3.12.

## Working on documentation

Improvements or additions to the project's documentation are highly appreciated.

The documentation is based on the [MkDocs](http://mkdocs.org) and [Material for MkDocs (`mkdocs-material`)](https://squidfunk.github.io/mkdocs-material/) projects, see their homepages for in-depth guides on their features and usage.
We use the [Numpy documentation style](https://numpydoc.readthedocs.io/en/latest/format.html) for Python docstrings.

To build the documentation locally, you need to first install the optional `docs` dependencies from `requirements-docs.txt`,
e.g., with `uv pip install -r requirements-docs.txt`.

You can then start a local documentation server with `mkdocs serve` (mkdocs listens on port 8000 by default),
or generate a static build under the `public/` folder using `mkdocs build`.

In order to maintain documentation for multiple versions of this library, we use the [mike](https://github.com/jimporter/mike) tool to
maintain individual documentation builds per version.

The GitHub CI pipeline automatically invokes `mike` as part of the release process with the correct version and updates the GitHub pages branch for the project.

## Contributions under repository license

Any contributions you make need to be under the same [Apache 2.0 License](https://github.com/aai-institute/jobq/blob/main/LICENSE) that covers the project.

See the [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#6-contributions-under-repository-license) for more details on this _inbound=outbound_ policy:

> Whenever you add Content to a repository containing notice of a license, you license that Content under the same terms, and you agree that you have the right to license that Content under those terms. If you have a separate agreement to license that Content under different terms, such as a contributor license agreement, that agreement will supersede.

> Isn't this just how it works already? Yep. This is widely accepted as the norm in the open-source community; it's commonly referred to by the shorthand "inbound=outbound". We're just making it explicit.
