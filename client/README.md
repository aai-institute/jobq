## Usage

If submitting to Kueue in a Minikube Kubernetes cluster, you need to configure your environment variables, so that images are available inside the cluster:

```
$ eval $(minikube -p minikube docker-env)
```

Then, you can execute a workload as a regular Python script:

```
$ python example_1.py
```

You can choose between the available execution modes (locally, in Docker, as a Kueue Kubernetes Job) by passing the `--mode` flag.
See the output of `--help` for allowed values.

## FAQ

- Q: Image build aborts with an exception `docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))`:
- A: If using Colima, might have to set `DOCKER_HOST` env var to point to the Colima Docker socket (obtain path from `docker context ls`)
