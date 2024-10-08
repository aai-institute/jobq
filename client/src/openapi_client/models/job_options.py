"""
the jobq cluster workflow management tool backend

Backend service for the appliedAI infrastructure product

The version of the OpenAPI document: 0.1.0
Generated by OpenAPI Generator (https://openapi-generator.tech)

Do not edit the class manually.
"""  # noqa: E501

from __future__ import annotations

import json
import pprint
import re  # noqa: F401
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, StrictStr
from typing_extensions import Self

from openapi_client.models.resource_options import ResourceOptions
from openapi_client.models.scheduling_options import SchedulingOptions


class JobOptions(BaseModel):
    """
    Options for customizing a Kubernetes job definition from a Python function.
    """  # noqa: E501

    resources: ResourceOptions | None = None
    scheduling: SchedulingOptions
    labels: dict[str, StrictStr] | None = None
    __properties: ClassVar[list[str]] = ["resources", "scheduling", "labels"]

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
        """Create an instance of JobOptions from a JSON string"""
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
        # override the default output from pydantic by calling `to_dict()` of resources
        if self.resources:
            _dict["resources"] = self.resources.to_dict()
        # override the default output from pydantic by calling `to_dict()` of scheduling
        if self.scheduling:
            _dict["scheduling"] = self.scheduling.to_dict()
        # set to None if resources (nullable) is None
        # and model_fields_set contains the field
        if self.resources is None and "resources" in self.model_fields_set:
            _dict["resources"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: dict[str, Any] | None) -> Self | None:
        """Create an instance of JobOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "resources": ResourceOptions.from_dict(obj["resources"])
            if obj.get("resources") is not None
            else None,
            "scheduling": SchedulingOptions.from_dict(obj["scheduling"])
            if obj.get("scheduling") is not None
            else None,
            "labels": obj.get("labels"),
        })
        return _obj
