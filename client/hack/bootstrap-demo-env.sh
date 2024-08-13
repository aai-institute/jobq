#!/bin/bash -eu

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"

COLIMA_CPUS=${COLIMA_CPUS:-6}
COLIMA_MEMORY=${COLIMA_MEMORY:-12}
COLIMA_DISK=${COLIMA_DISK:-60}
COLIMA_VM_TYPE=${COLIMA_VM_TYPE:-vz}

MINIKUBE_CPUS=${MINIKUBE_CPUS:-max}
MINIKUBE_MEMORY=${MINIKUBE_MEMORY:-10G}

KUEUE_VERSION=${KUEUE_VERSION:-v0.8.0}

echo "Installing minikube via Homebrew"
brew install minikube helm colima

echo "Setting up Colima VM"
colima start --network-address --cpu="$COLIMA_CPUS" --memory="$COLIMA_MEMORY" --disk="$COLIMA_DISK" --vm-type="$COLIMA_VM_TYPE"

echo "Creating Minikube cluster"
minikube start --driver=docker --cpus="$MINIKUBE_CPUS" --memory="$MINIKUBE_MEMORY" --addons="registry"
docker update --restart=unless-stopped minikube  # set appropriate restart policy
docker run --restart=unless-stopped --detach --name minikube-registry-proxy --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:5000,reuseaddr,fork TCP:$(minikube ip):5000"

echo "Installing Kueue & setting up single cluster queue"
kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/"$KUEUE_VERSION"/manifests.yaml
kubectl rollout status --timeout=60s -n kueue-system deployment/kueue-controller-manager
kubectl apply --server-side -f "$REPO_ROOT"/single-clusterqueue-setup.yaml

echo "Installing Kuberay operator"
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update
helm install --wait kuberay-operator kuberay/kuberay-operator
kubectl rollout status --timeout=60s deployment/kuberay-operator
