ARG PYTHON_VERSION=3.12-slim

# Build stage
FROM python:${PYTHON_VERSION} AS build

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade uv

# Explicitly set version number for setuptools-scm, since no .git folder is present
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AAI_JOBQ_SERVER=0.0.0

WORKDIR /code
COPY ./alembic.ini alembic.ini

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \ 
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY ./pyproject.toml ./uv.lock ./alembic.ini /code/
COPY ./src /code/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Runtime stage
FROM python:${PYTHON_VERSION}

WORKDIR /code
COPY scripts/entrypoint.sh /entrypoint.sh
COPY --chown=nobody:nogroup --from=build /code /code

USER nobody

ENV PYTHONUNBUFFERED=1

VOLUME ["/data"]

ENTRYPOINT ["/entrypoint.sh"]
