# JobOptions

JobOptions

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**resources** | [**ResourceOptions**](ResourceOptions.md) |  | [optional] 
**scheduling** | [**SchedulingOptions**](SchedulingOptions.md) |  | [optional] 
**labels** | **Dict[str, str]** |  | [optional] 

## Example

```python
from openapi_client.models.job_options import JobOptions

# TODO update the JSON string below
json = "{}"
# create an instance of JobOptions from a JSON string
job_options_instance = JobOptions.from_json(json)
# print the JSON string representation of the object
print(JobOptions.to_json())

# convert the object into a dict
job_options_dict = job_options_instance.to_dict()
# create an instance of JobOptions from a dict
job_options_from_dict = JobOptions.from_dict(job_options_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
