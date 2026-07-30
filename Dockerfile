FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .

ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_SEARCHY=0.1.0

RUN pip install --no-cache-dir .

COPY . .

RUN pip install --no-cache-dir .

CMD ["searchy-prod"]
