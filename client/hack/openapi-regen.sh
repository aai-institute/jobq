#!/bin/bash -eux

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../.. && pwd )"
fname=openapi-$(date +%s).json
curl -o "$REPO_ROOT/$fname" http://localhost:8000/openapi.json

docker run --rm \
    -v "$REPO_ROOT":/local \
    openapitools/openapi-generator-cli \
    generate \
    -i /local/"$fname" \
    -g python \
    -o /local/openapi-client \
    --additional-properties=generateSourceCodeOnly=true,packageName=openapi_client

cp -af "$REPO_ROOT"/openapi-client/openapi_client "$REPO_ROOT"/client/src

ruff format "$REPO_ROOT"/client/src/openapi_client/
ruff check --fix --unsafe-fixes "$REPO_ROOT"/client/src/openapi_client/
rm -rf "$REPO_ROOT"/openapi-client
rm "$REPO_ROOT/$fname"
