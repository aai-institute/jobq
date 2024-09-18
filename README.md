# Jobq: Multi-backend Job definition and Management from Python and the CLI

Jobq is a compute job definition, workflow management and scheduling tool that supports Kubernetes, Kueue, and Ray backends.

Define jobs in your `.py` files by using the `@job` decorator on the function that contains your compute logic.
Within the decorator you define the desired resources and link the environment configuration. We support Dockerfiles or a declarative `.yaml` file specification.
Using the `jobq` CLI you can execute jobs locally or submit them to one of the supported backends. 
Additionally, you can query for a job status and fetch logs.

Jobq is an early stage project, so expect rough edges. We are happy for feedback and may accomodate your feature requests, so don't hesitate to get in touch.
