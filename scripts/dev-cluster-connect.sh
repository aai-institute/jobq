#!/bin/bash -eux

# Set up an IAP tunnel to the GCE instance running the Mnikube cluster
# and configure kubectl to use the resulting kubeconfig.
#
# The instance is defined in the `GCE_INSTANCE` variable.

# Kill the entire process group if the script is terminated
trap 'kill -TERM -$$' SIGINT SIGTERM EXIT

GCE_INSTANCE="infra-product-dev-5bs1"

gcloud compute start-iap-tunnel --zone=europe-west3-c --local-host-port=localhost:8443 "$GCE_INSTANCE" 32771 &

sleep 1  # Allow time for the tunnel to be established

export KUBECONFIG=~/.kube/kubeconfig-playground
gcloud secrets versions access latest --secret=minikube-kubeconfig > $KUBECONFIG

# Select default namespace
kubectl config set-context --current --namespace=default

# Sanity check
kubectl get pods --all-namespaces

# Wait for user to terminate the script
read -n 1 -s -r -p "Press any key to stop the tunnel..."
