FROM python:3.11-slim-bookworm

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD src src
ADD pyproject.toml pyproject.toml
RUN pip install .

# allow imports from project root directory, FIXME: hacky
ENV PYTHONPATH=.
COPY *.py ./
