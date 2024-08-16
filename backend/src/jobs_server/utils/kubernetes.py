from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import kubernetes
from jobs.job import Job

from jobs_server.models import SubmissionContext


def sanitize_rfc1123_domain_name(s: str) -> str:
    """Sanitize a string to be compliant with RFC 1123 domain name

    Note: Any invalid characters are replaced with dashes."""

    # TODO: This is obviously wildly incomplete
    return s.replace("_", "-")


def k8s_annotations(
    job: Job, context: SubmissionContext | None = None
) -> dict[str, str]:
    """Determine the Kubernetes annotations for a Job"""
    # Store as annotations since labels have restrictive value formats
    options = job.options.labels if job.options else {}
    context = {"x-jobby.io/submission-context": json.dumps(context)} if context else {}
    return options | context


@dataclass
class GroupVersionKind:
    group: str
    version: str
    kind: str


class KubernetesObject(Protocol):
    @property
    def api_version(self) -> str: ...

    @property
    def kind(self) -> str: ...


def gvk(obj: KubernetesObject | dict[str, Any]) -> GroupVersionKind:
    kind = obj.kind if hasattr(obj, "kind") else obj["kind"]
    if "/" in (
        api_version := obj.api_version
        if hasattr(obj, "api_version")
        else obj["apiVersion"]
    ):
        group, version = api_version.split("/")
    else:
        group, version = "", api_version

    return GroupVersionKind(group, version, kind)


class KubernetesNamespaceMixin:
    """Determine the desired or current Kubernetes namespace."""

    def __init__(self, **kwargs):
        kubernetes.config.load_config()
        self._namespace: str | None = kwargs.get("namespace")

    @property
    def namespace(self) -> str:
        _, active_context = kubernetes.config.list_kube_config_contexts()
        current_namespace = active_context["context"].get("namespace")
        return self._namespace or current_namespace
