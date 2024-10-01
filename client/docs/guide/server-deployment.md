---
title: Server Deployment
---

# How to deploy a jobq server

This guide will walk you through the steps to deploy a jobq server to an existing Kubernetes cluster.

The following steps assume you already have a Kubernetes cluster set up and running.
If you need guidance on how to do this, please refer to the [Kubernetes documentation](https://kubernetes.io/docs/setup/){: target="\_blank" rel="noopener"} and check out [Minikube](https://minikube.sigs.k8s.io/docs/){: target="\_blank" rel="noopener"} if you want to try out a local Kubernetes cluster.

## Prerequisites

Before you can deploy a jobq server, you need to have the tools following installed on your machine:

-   [kubectl](https://kubernetes.io/docs/tasks/tools/){: target="\_blank" rel="noopener"}
-   [Helm](https://helm.sh/){: target="\_blank" rel="noopener"}

### Kueue

Jobq requires Kueue to be installed in the same Kubernetes cluster as a prerequisite. Please refer to the [Kueue documentation](https://kueue.sigs.k8s.io/docs/installation/){: target="\_blank" rel="noopener"} for more information on how to install Kueue.

If you want to install Kueue with default settings, you can do so by running the following command (optionally replacing `latest` with the desired version):

```console
kubectl apply --server-side -f \
    https://github.com/kubernetes-sigs/kueue/releases/latest/download/manifests.yaml
```

You also need to set up a few additional resources for Kueue to work properly:

-   a cluster queue ([`ClusterQueue` CRD](https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-ClusterQueue){: target="\_blank" })
-   a namespaced local queue ([`LocalQueue` CRD](https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-LocalQueue){: target="\_blank" })
-   a resource flavor ([`ResourceFlavor` CRD](https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-ResourceFlavor){: target="\_blank" })
-   optionally, one or more priority classes ([`WorkloadPriorityClass` CRD](https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta1/#kueue-x-k8s-io-v1beta1-WorkloadPriorityClass){: target="\_blank" })

For a quick start, the jobq repository contains a YAML file with a cluster queue `cluster-queue` with a default resource flavor `default-flavor`, a local queue `user-queue` and three priority classes `background`, `dev`, and `production`:

```console
$ kubectl apply --server-side -f \
    https://raw.githubusercontent.com/aai-institute/jobq/refs/heads/main/client/single-clusterqueue-setup.yaml
```

### Kuberay (optional)

If you want to submit [Ray](https://ray.io){: target="\_blank" } jobs to your Kubernetes cluster, you need to install the [Ray operator](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started.html){: target="\_blank" rel="noopener"} as well:

```console
$ helm repo add kuberay https://ray-project.github.io/kuberay-helm/
$ helm install --wait kuberay-operator kuberay/kuberay-operator
```

## :simple-helm: Deployment with Helm (recommended)

After settings up the prerequisites, you can use the following command to deploy the jobq server to your Kubernetes cluster:

```console
$ helm repo add jobq https://aai-institute.github.io/jobq
$ helm install --wait jobq jobq/jobq-server
```

This will install the jobq server in the currently active namespace.
You can change the namespace by passing the `--namespace` flag to the `helm install` command.

Please see the [README of the jobq Helm chart](https://github.com/aai-institute/jobq/tree/main/backend/deploy/jobq-server){: target="\_blank" } for more information on how to configure the jobq server.

!!! note

    Currently, the jobq server will only handle workloads in the namespace it is installed in.
    If you want to watch workloads in multiple namespaces, you will need to install the jobq server in each of those namespaces.

## :simple-docker: Running in a Docker container

While running the jobq server inside the Kubernetes cluster is the recommended setup, you can also run it in a Docker container:

```console
$ docker run \
    -v ${KUBECONFIG:-~/.kube/config}:/secrets/kubeconfig \
    -e KUBECONFIG=/secrets/kubeconfig \
    -p 8000:8000 \
    ghcr.io/aai-institute/jobq-server:main
```

This will make the jobq API available at `http://localhost:8000`.

Note that you will need to make sure that the container has network access to the Kubernetes API server and credentials to access it (e.g., by mounting the `~/.kube/config` file and setting the `KUBECONFIG` environment variable).

To prevent path errors related to CA certificates in the Kubeconfig file, you may want to generate a flattened version of the file to use for the mount:

```console
$ kubectl config view --flatten > /tmp/kubeconfig
```

If you are using Minikube or another local Kubernetes cluster, you may want to spawn the jobq container in host networking mode to allow it to access the Kubernetes API server:

```console
$ docker run \
    --network host \
    -v ${KUBECONFIG:-~/.kube/config}:/secrets/kubeconfig \
    -e KUBECONFIG=/secrets/kubeconfig \
    ghcr.io/aai-institute/jobq-server:main
```
