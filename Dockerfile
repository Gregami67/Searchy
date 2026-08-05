FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu .

COPY . .

RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu .

CMD ["searchy-prod"]
