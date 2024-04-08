FROM python:3.12-slim-bookworm

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD src src
ADD pyproject.toml pyproject.toml
RUN pip install .

ADD example_1.py example_1.py
