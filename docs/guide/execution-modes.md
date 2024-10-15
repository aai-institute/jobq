---
title: Job execution modes
---

# Choosing an execution mode for your job

## Understanding execution modes

Jobq allows you to run your jobs in different execution modes (through the `jobq submit --mode` parameter), in some cases even without any changes to your code.

Execution modes determine how your job is executed, where it runs, and how resources are managed. The choice of execution mode depends on your requirements, such as the scale of your job, the resources it needs, and the frameworks and libraries you are using in your code.

For example, if you are running a small job that does not require any external dependencies, you can submit your job as a "plain" Kubernetes batch job. However, if you are performing large-scale machine learning training, you might want to use a Ray job to distribute your workload across multiple compute nodes.

### Local execution

The most basic execution mode is `local`, which runs your job as a Python function on the same machine where the jobq client is executed. This mode does not provide any of the benefits such as automatic resource management, but it is the fastest way to get started.

As an additional benefit, since you are running your job locally, you can easily debug your code and test it on a small scale before scaling it up to a cluster-based execution mode.
Breakpoints, logging, and other debugging tools work as expected in this mode.

### Cluster-based execution

The more advanced execution modes require a backend to run your job and a Kubernetes cluster where the job can be scheduled and executed. All Kubernetes-based execution modes are built on top of [Kueue](https://kueue.sigs.k8s.io/), a Kubernetes-native job scheduling system, and extend its underlying functionality.

Currently, jobq supports two cluster-based execution modes:

-   **[Kueue Mode](#kubernetes-batch-jobs)**: This mode runs your job as a Kubernetes built-in `batch/v1/Job`.
-   **[Ray Job Mode](#ray-jobs)**: This mode runs your job in an ephemeral [Ray cluster](https://docs.ray.io/en/latest/cluster/getting-started.html), which is automatically created and destroyed for each job.

<!-- TODO: Reword the below sections once job execution parametrization is implemented -->

#### Kubernetes batch jobs

By default, Kubernetes batch jobs are submitted using the following default parameters:

-   Job parallelism is set to 1
-   Image pull policy is set to `IfNotPresent`
-   Backoff limit set to 6 (exponential backoff applies to retried jobs)
-   Resource requests are applied as `limits == requests`

#### Ray jobs

The default options for Ray jobs submitted by jobq are as follows:

-   Single head node, no worker nodes
-   Job clusters are shut down automatically after job finishes
-   Job image is used for worker nodes and job submission pod
-   Image pull policy is set to `IfNotPresent`
-   Resource requests are applied as `limits == requests`

## Choosing an execution mode

When choosing an execution mode for your job, consider the following factors:

-   **Integration with other code**: If you are using a specific framework or library that requires a specific execution mode, you may need to choose an execution mode that best supports that framework or library (e.g., submit Ray jobs as such, although they could also be submitted as a plain job which spins up an ephemeral one-node Ray cluster.).
-   **Resource requirements**: Different execution modes have different resource requirements. For example, Ray jobs require more resources than Kubernetes batch jobs due to the overhead of running the components Ray control plane.
-   **Scaling needs**: If you need to scale your job across multiple nodes, you may need to choose an execution mode that supports distributed computing, such as Ray jobs. In addition, frameworks like Ray provide support for [autoscaling based on resource demand](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/configuring-autoscaling.html), which can help you scale your cluster dynamically based on the workload.
-   **Runtime observability**: If you need to introspect the runtime environment of your job, such as the number of nodes, CPU and memory usage, and other metrics, you may need to choose an execution mode that provides this information. For example, Ray exposes a variety of [metrics](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/observability.html) that can be used to monitor the performance of a Ray cluster and jobs submitted to it.

As a general guideline, you can start with local execution mode for development and testing, and then switch to a cluster-based execution mode for production workloads.
Local execution allows you to easily debug your code and test it on a small scale, while cluster-based execution modes provide better resource management and scalability for large-scale jobs, especially when working in a team of multiple developers.
