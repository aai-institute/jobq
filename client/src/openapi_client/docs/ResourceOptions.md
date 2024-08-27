# ResourceOptions

ResourceOptions

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**memory** | **str** |  | [optional] 
**cpu** | **str** |  | [optional] 
**gpu** | **int** |  | [optional] 

## Example

```python
from openapi_client.models.resource_options import ResourceOptions

# TODO update the JSON string below
json = "{}"
# create an instance of ResourceOptions from a JSON string
resource_options_instance = ResourceOptions.from_json(json)
# print the JSON string representation of the object
print(ResourceOptions.to_json())

# convert the object into a dict
resource_options_dict = resource_options_instance.to_dict()
# create an instance of ResourceOptions from a dict
resource_options_from_dict = ResourceOptions.from_dict(resource_options_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


