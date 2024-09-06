"""
infrastructure-product API

Backend service for the appliedAI infrastructure product

The version of the OpenAPI document: 0.1.0
Generated by OpenAPI Generator (https://openapi-generator.tech)

Do not edit the class manually.
"""  # noqa: E501

from __future__ import annotations

import json
import pprint
import re  # noqa: F401
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr
from typing_extensions import Self

from openapi_client.models.job_status import JobStatus
from openapi_client.models.workload_spec import WorkloadSpec
from openapi_client.models.workload_status import WorkloadStatus


class WorkloadMetadata(BaseModel):
    """
    WorkloadMetadata
    """  # noqa: E501

    managed_resource_id: StrictStr
    execution_status: JobStatus
    spec: WorkloadSpec
    kueue_status: WorkloadStatus
    submission_timestamp: datetime
    last_admission_timestamp: datetime | None = None
    termination_timestamp: datetime | None = None
    was_evicted: StrictBool | None = False
    was_inadmissible: StrictBool | None = False
    __properties: ClassVar[list[str]] = [
        "managed_resource_id",
        "execution_status",
        "spec",
        "kueue_status",
        "submission_timestamp",
        "last_admission_timestamp",
        "termination_timestamp",
        "was_evicted",
        "was_inadmissible",
    ]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self | None:
        """Create an instance of WorkloadMetadata from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: set[str] = set()

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of spec
        if self.spec:
            _dict["spec"] = self.spec.to_dict()
        # override the default output from pydantic by calling `to_dict()` of kueue_status
        if self.kueue_status:
            _dict["kueue_status"] = self.kueue_status.to_dict()
        # set to None if last_admission_timestamp (nullable) is None
        # and model_fields_set contains the field
        if (
            self.last_admission_timestamp is None
            and "last_admission_timestamp" in self.model_fields_set
        ):
            _dict["last_admission_timestamp"] = None

        # set to None if termination_timestamp (nullable) is None
        # and model_fields_set contains the field
        if (
            self.termination_timestamp is None
            and "termination_timestamp" in self.model_fields_set
        ):
            _dict["termination_timestamp"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: dict[str, Any] | None) -> Self | None:
        """Create an instance of WorkloadMetadata from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "managed_resource_id": obj.get("managed_resource_id"),
            "execution_status": obj.get("execution_status"),
            "spec": WorkloadSpec.from_dict(obj["spec"])
            if obj.get("spec") is not None
            else None,
            "kueue_status": WorkloadStatus.from_dict(obj["kueue_status"])
            if obj.get("kueue_status") is not None
            else None,
            "submission_timestamp": obj.get("submission_timestamp"),
            "last_admission_timestamp": obj.get("last_admission_timestamp"),
            "termination_timestamp": obj.get("termination_timestamp"),
            "was_evicted": obj.get("was_evicted")
            if obj.get("was_evicted") is not None
            else False,
            "was_inadmissible": obj.get("was_inadmissible")
            if obj.get("was_inadmissible") is not None
            else False,
        })
        return _obj
