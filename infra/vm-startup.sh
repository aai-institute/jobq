#!/bin/bash

set -ux

# --- Install Docker Engine
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
    apt-get remove -y $pkg
done

# Add Docker's official GPG key:
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update

apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# --- Install Minikube and create cluster
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb
sudo dpkg -i minikube_latest_amd64.deb

# -- Install kubectl, helm, skaffold
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
sudo install skaffold /usr/local/bin/

# -- Provision default user
adduser playground --disabled-password
usermod -aG sudo,docker playground 

cat <<'EOF' | sudo -u playground bash
[ -f "/home/playground/.ssh/id_ed25519" ] || ssh-keygen -t ed25519 -f /home/playground/.ssh/id_ed25519 -N ""

minikube start --driver=docker --cpus=max --memory=28G --disk-size=64g --listen-address=0.0.0.0

# Upload kubeconfig (for local forwarding) to Secret Manager, including CA certificate
minikube update-context
minikube kubectl -- config view --flatten | sed 's|server: https://192.168.49.2:8443|server: https://127.0.0.1:8443|g' > /home/playground/kubeconfig
gcloud secrets versions add minikube-kubeconfig --data-file=/home/playground/kubeconfig

gcloud auth configure-docker europe-west3-docker.pkg.dev --quiet
EOF
