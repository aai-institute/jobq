#!/bin/bash -eu

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"

docker run -it --rm -p 8080:8080 -v "$REPO_ROOT"/architecture/structurizr:/usr/local/structurizr structurizr/lite
