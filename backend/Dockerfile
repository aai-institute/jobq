ARG PYTHON_VERSION=3.12-slim

# Build stage
FROM python:${PYTHON_VERSION} AS build

RUN apt-get update && \
    apt-get install -y git libhdf5-dev pkg-config build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade uv

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN uv venv --seed && \
    uv pip install -r requirements.txt

COPY ./pyproject.toml /code/pyproject.toml
COPY ./src /code/src
RUN uv pip install --no-deps .

# Runtime stage
FROM python:${PYTHON_VERSION}

WORKDIR /code
COPY --from=build /code /code

CMD ["/code/.venv/bin/uvicorn", "jobq_server.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
