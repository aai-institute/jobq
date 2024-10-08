# Declarative Container Configuration

jobq allows you to define your container image in a declarative YAML format instead of writing a Dockerfile.

## YAML Structure

The YAML structure, for the most part, mirrors the structure of a Dockerfile.
We only provide an abstraction around the dependencies map.
Hence, the official [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) may be helpful to understand the meaning of different options. 

A full example of a declarative YAML looks like this:
```yaml
build:
  base_image: <base_image>
  dependencies:
    apt: [<apt_packages>]
    pip: [<pip_packages>]
  volumes:
    - <container_path>
  user:
    name: <username>
  config:
    env:
      <env_var>: <value>
    arg:
      <build_arg>: <value>
    stopsignal: <signal>
    shell: <shell>
  meta:
    labels:
      <label_key>: <label_value>
  workdir: <working_directory>
  filesystem:
    copy:
      <src>: <dest>
    add:
      <src>: <dest>
```
Let us walk through an example of each of the options.

The YAML file uses a `build` key as the root, under which various aspects of the Docker image are defined.

First, you have to first specify the base image of the Dockerfile, for example:

```yaml
build:
  base_image: python:3.12-slim
```

Then, you can define system level and Python dependencies.
The system level dependencies require a Debian or Ubuntu derived base image to ensure the availability of `apt`.

The Python dependencies can be regular package dependencies, but you can also supply requirements files by prefixing them with `-r` or `--requirement` as well as wheel, `.whl`, files in the build context and editable local installs with `-e`.
The latter require that the source directory contains a `pyproject.toml`.


```yaml
build:
  dependencies:
    apt: [curl, git]
    pip: [attrs, pyyaml, test.whl, marker-package, -e ., -r requirements.txt]
```
In order to make directories or files within the container mountable, they have to be declared at build time. 

```yaml
build:
  volumes:
    - /mountable/path
```
You can also define user information for running the container.
```yaml
build:
  user:
    name: no_admin
```
If applicable you can set specific configuration options such as secrets, build arguments, etc.
You can supply the environment and build arguments either as a dictionary
```yaml
build:
  config:
    env:
      var: secret
    arg:
      build_arg: config
    stopsignal: 1
    shell: sh
```

Or as a list
```yaml
build:
  config:
    env:
      - var=secret
    arg:
      - build_arg=config
```

To control the execution environment in the container and during the build process, configure the working directory and filesystem.
They can be submitted as a dictionary: 
```yaml
build:
  workdir: /usr/src/
  filesystem:
    copy:
      source: target
    add:
      source: target
```
Or as a list of strings:
```yaml
build:
  workdir: /usr/src/
  filesystem:
    copy:
      - source=target
    add:
      - source=target
```

Lastly, you can add metadata as per your convenience.
You can again supply them either as a dict: 
```yaml
build:
  meta:
    labels:
      test: test
```
Or as a list of key value pairs
```yaml
build:
  meta:
    labels:
      - test=test
```

To use the container image, you have to add it in your `@job` decorator as a `spec`.
```python
from jobq.job import Job, JobOptions, ImageOptions
from pathlib import Path

@job(
    options=JobOptions(...),
    image=ImageOptions(
        spec=Path("path/to/your/docker.yaml"),
        name="your-image-name",
        tag="your-tag"
    )
)
def your_job_function():
    pass
```
Now you can submit a job with the jobq CLI.
jobq will automatically generate a Dockerfile from your YAML configuration when building the image for your job.
If you submit a Dockerfile directly, it will be used.
