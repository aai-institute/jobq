---
title: Job execution modes
---

# Choosing an execution mode for your job

## Understanding execution modes

Jobq allows you to run your jobs in different execution modes, sometimes even without any changes to your code.

### Local Execution Mode

The most basic execution mode is `local`, which runs your job as a Python function on the same machine where the jobq client is running. This mode does not provide any of the benefits such as automatic resource management, but it is the fastest way to get started.

### Cluster-Based Execution Modes

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

TODO
