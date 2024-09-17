import * as gcp from "@pulumi/gcp";
import * as pulumi from "@pulumi/pulumi";
import * as fs from "fs";

const gcp_config = new pulumi.Config("gcp");
const region = gcp_config.require("region");
const project = gcp_config.require("project");
const zone = gcp_config.require("zone");

// VPC network
const network = gcp.compute.getNetwork({
    name: "infra-product-dev",
});
const subnet = "compute";

// VM for Playground
const sa = new gcp.serviceaccount.Account("playground", {
    accountId: "playground",
    displayName: "Service account for Playground VM",
});
// Application roles for SA, including Ops Agent (Logs & Metric Writer)
for (const role of [
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.admin",
    "roles/secretmanager.secretVersionAdder",
]) {
    new gcp.projects.IAMMember(`playground-${role}`, {
        project,
        member: pulumi.concat("serviceAccount:", sa.email),
        role,
    });
}

const instanceTemplate = new gcp.compute.InstanceTemplate("infra-product-dev", {
    region,
    machineType: "e2-standard-8",
    disks: [
        {
            boot: true,
            sourceImage: "debian-cloud/debian-12",
            diskSizeGb: 100,
            diskType: "pd-balanced",
        },
    ],
    metadataStartupScript: fs.readFileSync("./vm-startup.sh", "utf-8"),
    networkInterfaces: [
        {
            network: network.then((n) => n.id),
            subnetwork: subnet,
            accessConfigs: [
                {
                    networkTier: "PREMIUM",
                },
            ],
        },
    ],
    tags: ["ssh"],
    labels: {
        environment: "playground",
    },
    serviceAccount: {
        email: sa.email,
        scopes: ["https://www.googleapis.com/auth/cloud-platform"],
    },
    scheduling: {
        preemptible: true,
        automaticRestart: false, // required for preemptible instances
    },
});

const instanceGroupManager = new gcp.compute.InstanceGroupManager(
    "playground",
    {
        zone,
        versions: [
            {
                instanceTemplate: instanceTemplate.id,
            },
        ],

        namedPorts: [
            {
                name: "k8s",
                port: 32771, // Minikube always maps to the same high-number ports starting from 32768, 32771 corresponds to the apiserver
            },
        ],
        baseInstanceName: "infra-product-dev",
        targetSize: 1,
    },
);

// Load balancer for the instance group
const healthCheck = new gcp.compute.HealthCheck("playground-k8s", {
    checkIntervalSec: 10,
    timeoutSec: 5,
    healthyThreshold: 2,
    unhealthyThreshold: 10,
    httpsHealthCheck: {
        portName: "k8s",
        requestPath: "/healthz",
    },
});
const be = new gcp.compute.BackendService("playground-k8s", {
    backends: [
        {
            group: instanceGroupManager.instanceGroup,
        },
    ],
    portName: "k8s",
    protocol: "HTTPS",
    loadBalancingScheme: "INTERNAL_MANAGED",
    healthChecks: healthCheck.id,
});

new gcp.compute.Firewall("inbound-lb", {
    network: network.then((n) => n.id),
    sourceRanges: [
        "35.191.0.0/16",
        "130.211.0.0/22", // Load balancer health checks
        "35.235.240.0/20", // IAP
    ],
    targetServiceAccounts: [sa.email],
    allows: [
        {
            protocol: "TCP",
            ports: ["22", "32771"],
        },
    ],
    direction: "INGRESS",
});
new gcp.compute.Firewall("inbound-from-iap", {
    network: network.then((n) => n.id),
    sourceRanges: ["35.235.240.0/20"],
    targetServiceAccounts: [sa.email],
    allows: [
        {
            protocol: "TCP",
        },
    ],
    direction: "INGRESS",
});

// Artifact Registry
const repo = new gcp.artifactregistry.Repository("dev", {
    format: "Docker",
    repositoryId: "infra-product-dev",
    location: region,
});
new gcp.artifactregistry.RepositoryIamMember("public-pull", {
    repository: repo.id,
    member: "allUsers",
    role: "roles/artifactregistry.reader",
});

// Secret Manager
new gcp.secretmanager.Secret("minikube-kubeconfig", {
    secretId: "minikube-kubeconfig",
    replication: {
        auto: {},
    },
});
