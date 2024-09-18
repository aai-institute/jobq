from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from jobq.job import Job
from kubernetes import client

from jobq_server.utils.helpers import traverse

if TYPE_CHECKING:
    from jobq_server.models import SubmissionContext


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
    context = {"x-jobq.io/submission-context": json.dumps(context)} if context else {}
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
    kind = traverse(obj, "kind")
    if "/" in (
        api_version := traverse(obj, "api_version", strict=False)
        or traverse(obj, "apiVersion", strict=False)
    ):
        group, version = api_version.split("/")
    else:
        group, version = "", api_version

    return GroupVersionKind(group, version, kind)


def filter_conditions(
    obj: Any,
    typ: str | None = None,
    reason: str | None = None,
    message: str | None = None,
    status: bool | None = None,
):
    """
    Filters Kubernetes object conditions based on specified attributes.

    This function filters the `status.conditions` field of a Kubernetes object
    by matching conditions against the provided `type`, `reason`, and `message`
    attributes. Only conditions that match all specified attributes are included
    in the result.

    Parameters
    ----------
    obj : dict[str, Any]
        The Kubernetes object, typically a dictionary representing a Kubernetes
        resource, containing a `status.conditions` field.
    typ : str, optional
        The type of condition to filter by. If `None`, this filter is not applied.
    reason : str, optional
        The reason attribute to filter by. If `None`, this filter is not applied.
    message : str, optional
        The message attribute to filter by. If `None`, this filter is not applied.
    status: bool, optional
        The status flag to filter by. If `None`, this filter is not applied.

    Returns
    -------
    list[dict[str, Any]]
        A list of conditions that match the specified filters. Each condition
        is represented as a dictionary.

    Notes
    -----
    - The function assumes that the `status.conditions` field exists in the
      provided object and that it is a list of condition dictionaries.
    - If no conditions match the specified filters, an empty list is returned.

    Examples
    --------
    >>> obj = {
    ...     "status": {
    ...         "conditions": [
    ...             {"type": "Ready", "reason": "DeploymentCompleted", "message": "Deployment successful."},
    ...             {"type": "Failed", "reason": "DeploymentFailed", "message": "Deployment failed due to timeout."}
    ...         ]
    ...     }
    ... }
    >>> filter_conditions(obj, typ="Ready")
    [{'type': 'Ready', 'reason': 'DeploymentCompleted', 'message': 'Deployment successful.'}]

    >>> filter_conditions(obj, reason="DeploymentFailed")
    [{'type': 'Failed', 'reason': 'DeploymentFailed', 'message': 'Deployment failed due to timeout.'}]
    """

    def _safe_bool(s: str | bool) -> bool:
        if isinstance(s, bool):
            return s
        ls = s.lower()
        if ls == "true":
            return True
        elif ls == "false":
            return False
        else:
            raise ValueError(f"unexpected string literal {s!r}")

    def _match(cond):
        return all([
            typ is None or cond["type"] == typ,
            reason is None or cond["reason"] == reason,
            message is None or cond["message"] == message,
            status is None or _safe_bool(cond["status"]) == status,
        ])

    return [cond for cond in traverse(obj, "status.conditions") if _match(cond)]


class AttributeMapping(Protocol):
    attribute_map: dict[str, str]


T = TypeVar("T", bound=AttributeMapping)


def build_metadata(
    obj: dict[str, Any] | client.V1ObjectMeta,
) -> client.V1ObjectMeta:
    """Instantiate a Kubernetes object metadata from a dictionary or existing instance."""

    def _attribute_name(attribute_map: dict[str, str], attribute: str) -> str:
        """Convert an attribute name in a dict to snake case name in a Kubernetes object."""
        return next(k for k, v in attribute_map.items() if v == attribute)

    def _make(cls: type[T], obj: dict[str, Any]) -> T:
        """Map a dictionary to a Kubernetes object non-recursively."""
        return cls(**{_attribute_name(cls.attribute_map, k): v for k, v in obj.items()})

    if isinstance(obj, client.V1ObjectMeta):
        return obj

    metadata = _make(client.V1ObjectMeta, obj)
    if metadata.owner_references:
        metadata.owner_references = [
            _make(client.V1OwnerReference, ref) for ref in metadata.owner_references
        ]
    if metadata.managed_fields:
        metadata.managed_fields = [
            _make(client.V1ManagedFieldsEntry, ref) for ref in metadata.managed_fields
        ]
    return metadata
