# CreateJobModel


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**file** | **str** |  | 
**image_ref** | **str** |  | 
**mode** | [**ExecutionMode**](ExecutionMode.md) |  | 
**options** | [**JobOptions**](JobOptions.md) |  | 
**submission_context** | **object** |  | [optional] 

## Example

```python
from openapi_client.models.create_job_model import CreateJobModel

# TODO update the JSON string below
json = "{}"
# create an instance of CreateJobModel from a JSON string
create_job_model_instance = CreateJobModel.from_json(json)
# print the JSON string representation of the object
print(CreateJobModel.to_json())

# convert the object into a dict
create_job_model_dict = create_job_model_instance.to_dict()
# create an instance of CreateJobModel from a dict
create_job_model_from_dict = CreateJobModel.from_dict(create_job_model_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
