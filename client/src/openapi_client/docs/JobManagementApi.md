# openapi_client.JobManagementApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**logs_jobs_uid_logs_get**](JobManagementApi.md#logs_jobs_uid_logs_get) | **GET** /jobs/{uid}/logs | Logs
[**status_jobs_uid_status_get**](JobManagementApi.md#status_jobs_uid_status_get) | **GET** /jobs/{uid}/status | Status
[**stop_workload_jobs_uid_stop_post**](JobManagementApi.md#stop_workload_jobs_uid_stop_post) | **POST** /jobs/{uid}/stop | Stop Workload
[**submit_job_jobs_post**](JobManagementApi.md#submit_job_jobs_post) | **POST** /jobs | Submit Job


# **logs_jobs_uid_logs_get**
> object logs_jobs_uid_logs_get(uid, stream=stream, tail=tail, namespace=namespace)

Logs

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobManagementApi(api_client)
    uid = 'uid_example' # str | 
    stream = False # bool |  (optional) (default to False)
    tail = 100 # int |  (optional) (default to 100)
    namespace = 'default' # str |  (optional) (default to 'default')

    try:
        # Logs
        api_response = api_instance.logs_jobs_uid_logs_get(uid, stream=stream, tail=tail, namespace=namespace)
        print("The response of JobManagementApi->logs_jobs_uid_logs_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobManagementApi->logs_jobs_uid_logs_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 
 **stream** | **bool**|  | [optional] [default to False]
 **tail** | **int**|  | [optional] [default to 100]
 **namespace** | **str**|  | [optional] [default to &#39;default&#39;]

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **status_jobs_uid_status_get**
> object status_jobs_uid_status_get(uid, namespace=namespace)

Status

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobManagementApi(api_client)
    uid = 'uid_example' # str | 
    namespace = 'default' # str |  (optional) (default to 'default')

    try:
        # Status
        api_response = api_instance.status_jobs_uid_status_get(uid, namespace=namespace)
        print("The response of JobManagementApi->status_jobs_uid_status_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobManagementApi->status_jobs_uid_status_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 
 **namespace** | **str**|  | [optional] [default to &#39;default&#39;]

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **stop_workload_jobs_uid_stop_post**
> stop_workload_jobs_uid_stop_post(uid, namespace=namespace)

Stop Workload

### Example


```python
import openapi_client
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobManagementApi(api_client)
    uid = 'uid_example' # str | 
    namespace = 'default' # str |  (optional) (default to 'default')

    try:
        # Stop Workload
        api_instance.stop_workload_jobs_uid_stop_post(uid, namespace=namespace)
    except Exception as e:
        print("Exception when calling JobManagementApi->stop_workload_jobs_uid_stop_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **uid** | **str**|  | 
 **namespace** | **str**|  | [optional] [default to &#39;default&#39;]

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **submit_job_jobs_post**
> WorkloadIdentifier submit_job_jobs_post(create_job_model)

Submit Job

### Example


```python
import openapi_client
from openapi_client.models.create_job_model import CreateJobModel
from openapi_client.models.workload_identifier import WorkloadIdentifier
from openapi_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = openapi_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with openapi_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = openapi_client.JobManagementApi(api_client)
    create_job_model = openapi_client.CreateJobModel() # CreateJobModel | 

    try:
        # Submit Job
        api_response = api_instance.submit_job_jobs_post(create_job_model)
        print("The response of JobManagementApi->submit_job_jobs_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling JobManagementApi->submit_job_jobs_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **create_job_model** | [**CreateJobModel**](CreateJobModel.md)|  | 

### Return type

[**WorkloadIdentifier**](WorkloadIdentifier.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

