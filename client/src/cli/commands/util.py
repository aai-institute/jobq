import openapi_client
from openapi_client.exceptions import ApiException

# TODO: Factor backend host url into some kind of config file
BACKEND_HOST = "http://localhost:8000"


def _make_api_client() -> openapi_client.ApiClient:
    api_config = openapi_client.Configuration(host=BACKEND_HOST)
    return openapi_client.ApiClient(api_config)


def handle_api_exception(e: ApiException, op: str) -> None:
    print(f"Error during workload {op}:")
    if e.status == 404:
        print(
            "Error: Workload not found. It may have been terminated or never existed."
        )
    else:
        print(f"Status: {e.status} - {e.reason}")
