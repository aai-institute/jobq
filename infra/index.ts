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

// VM for Dagster
const sa = new gcp.serviceaccount.Account("playground", {
  accountId: "playground",
  displayName: "Service account for Playground VM",
});
// Application roles for SA, including Ops Agent (Logs & Metric Writer)
for (const role of [
  "roles/logging.logWriter",
  "roles/monitoring.metricWriter",
  "roles/artifactregistry.admin",
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
      diskSizeGb: 64,
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

new gcp.compute.InstanceGroupManager("playground", {
  zone,
  versions: [
    {
      instanceTemplate: instanceTemplate.id,
    },
  ],

  baseInstanceName: "infra-product-dev",
  targetSize: 1,
});

new gcp.compute.Firewall("inbound-ssh-from-iap", {
  network: network.then((n) => n.id),
  sourceRanges: ["35.235.240.0/20"],
  targetServiceAccounts: [sa.email],
  allows: [
    {
      protocol: "TCP",
      ports: ["22"],
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
