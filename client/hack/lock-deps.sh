#!/bin/bash

set -eux

uv pip compile --strip-extras -o requirements.txt pyproject.toml
uv pip compile --all-extras -o requirements-dev.txt pyproject.toml
