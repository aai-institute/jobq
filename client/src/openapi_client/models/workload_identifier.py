import pprint
from pydantic import BaseModel, ConfigDict, StrictStr

from jobs.types import DictSerializable, JsonSerializable


class WorkloadIdentifier(DictSerializable, JsonSerializable, BaseModel):
    """Identifier for a workload in a Kubernetes cluster"""

    group: StrictStr
    version: StrictStr
    kind: StrictStr

    namespace: StrictStr
    uid: StrictStr

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))
