#!/usr/bin/env bash

set -eux

/code/.venv/bin/alembic upgrade head
/code/.venv/bin/uvicorn jobq_server.__main__:app --host 0.0.0.0 --port 8000 "$@"
