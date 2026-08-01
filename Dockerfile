FROM python:3.12-slim

ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir .

COPY . .

RUN pip install --no-cache-dir .

CMD ["searchy-prod"]
