import logging
import random
import shlex
import string
from dataclasses import asdict

import yaml
from jobs import Image, Job
from jobs.types import K8sResourceKind
from kubernetes import client

from jobs_server.models import ExecutionMode, SubmissionContext, WorkloadIdentifier
from jobs_server.runner.base import Runner, _make_executor_command
from jobs_server.services.k8s import KubernetesService
from jobs_server.utils.k8s import (
    gvk,
    k8s_annotations,
    sanitize_rfc1123_domain_name,
)
from jobs_server.utils.kueue import kueue_scheduling_labels


class RayJobRunner(Runner):
    """Job runner that submits ``RayJob`` resources to a Kubernetes cluster running the Kuberay operator."""

    def __init__(self, k8s: KubernetesService, **kwargs):
        super().__init__(**kwargs)

        self._k8s = k8s

    def _create_ray_job(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> dict:
        """Create a ``RayJob`` Kubernetes resource for the Kuberay operator."""

        if job.options is None:
            raise ValueError("Job options must be set")

        res_opts = job.options.resources
        if not res_opts:
            raise ValueError("Job resource options must be set")

        scheduling_labels = kueue_scheduling_labels(job, self._k8s.namespace)

        runtime_env = {
            "working_dir": "/home/ray/app",
        }

        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        job_id = f"{job.name}-{suffix}"

        # FIXME: Image pull policy should be configurable
        # It is currently hardcoded to "IfNotPresent" to support running
        # the E2E tests in a cluster without a proper image registry.
        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayJob",
            "metadata": {
                "name": sanitize_rfc1123_domain_name(job_id),
                "labels": scheduling_labels,
                "annotations": k8s_annotations(job, context),
            },
            "spec": {
                "jobId": job_id,
                "suspend": True,
                "entrypoint": shlex.join(_make_executor_command(job)),
                "runtimeEnvYAML": yaml.dump(runtime_env),
                "shutdownAfterJobFinishes": True,
                "rayClusterSpec": {
                    "rayVersion": "2.34.0",  # FIXME: Hardcoded, obtain thru job options
                    "headGroupSpec": {
                        "rayStartParams": {
                            "dashboard-host": "0.0.0.0",
                            "disable-usage-stats": "true",
                        },
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": "head",
                                        "image": image.tag,
                                        "imagePullPolicy": "IfNotPresent",
                                        "resources": {
                                            "requests": res_opts.to_kubernetes(
                                                kind=K8sResourceKind.REQUESTS
                                            ),
                                            "limits": res_opts.to_kubernetes(
                                                kind=K8sResourceKind.LIMITS
                                            ),
                                        },
                                    },
                                ]
                            }
                        },
                    },
                },
                "submitterPodTemplate": {
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "ray-submit",
                                "image": image.tag,
                                "imagePullPolicy": "IfNotPresent",
                            }
                        ],
                    },
                },
            },
        }

        return manifest

    def run(
        self, job: Job, image: Image, context: SubmissionContext
    ) -> WorkloadIdentifier:
        logging.info(
            f"Submitting RayJob {job.name} to namespace {self._k8s.namespace!r}"
        )

        manifest = self._create_ray_job(job, image, context)
        api = client.CustomObjectsApi()
        obj = api.create_namespaced_custom_object(
            "ray.io", "v1", self._k8s.namespace, "rayjobs", manifest
        )

        return WorkloadIdentifier(
            **asdict(gvk(obj)),
            name=obj["metadata"]["name"],
            namespace=obj["metadata"]["namespace"],
            uid=obj["metadata"]["uid"],
        )


Runner.register_implementation(RayJobRunner, ExecutionMode.RAYJOB)
