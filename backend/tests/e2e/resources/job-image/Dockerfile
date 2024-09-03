FROM debian:bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*
COPY jobs_execute /usr/local/bin/jobs_execute
COPY ray /usr/local/bin/ray
