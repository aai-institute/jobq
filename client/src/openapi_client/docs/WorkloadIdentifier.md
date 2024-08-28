# WorkloadIdentifier

Identifier for a workload in a Kubernetes cluster

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**group** | **str** |  | 
**version** | **str** |  | 
**kind** | **str** |  | 
**namespace** | **str** |  | 
**uid** | **str** |  | 

## Example

```python
from openapi_client.models.workload_identifier import WorkloadIdentifier

# TODO update the JSON string below
json = "{}"
# create an instance of WorkloadIdentifier from a JSON string
workload_identifier_instance = WorkloadIdentifier.from_json(json)
# print the JSON string representation of the object
print(WorkloadIdentifier.to_json())

# convert the object into a dict
workload_identifier_dict = workload_identifier_instance.to_dict()
# create an instance of WorkloadIdentifier from a dict
workload_identifier_from_dict = WorkloadIdentifier.from_dict(workload_identifier_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
