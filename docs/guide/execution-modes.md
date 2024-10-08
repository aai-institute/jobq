---
title: Job execution modes
---

# Choosing an execution mode for your job

## Understanding execution modes

Jobq allow you to run your jobs in different execution modes, sometimes even without any changes to your code.

The most basic execution mode is `local`, which runs your job as a Python function on the same machine where the jobq client is running.
This mode does not provide any of the benefits such as automatic resource management, but it is the fastest way to get started.

The more advanced execution modes require a backend to run your job and a Kubernetes cluster where the job can be scheduled and executed.

All Kubernetes-based execution modes are built on top of [Kueue](https://kueue.sigs.k8s.io/), a Kubernetes-native job scheduling system and extend its underlying functionality.

Currently, jobq supports two cluster-based execution modes:

-   `kueue`: This mode runs your job as a Kubernetes built-in `batch/v1/Job`.
-   `rayjob`: This mode runs your job in an ephemeral [Ray cluster](https://docs.ray.io/en/latest/cluster/getting-started.html), which is automatically created and destroyed for each job.

## Choosing an execution mode

TODO
