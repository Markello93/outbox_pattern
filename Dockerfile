FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  POETRY_VERSION=1.6.1 \
  PYTHONPATH=/app

RUN apt-get update --fix-missing \
  && apt-get install -y --no-install-recommends build-essential curl \
  && pip install --no-cache-dir --upgrade pip setuptools \
  && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --with dev --with test --without-hashes -o requirements.txt \
  && pip install --no-cache-dir -r requirements.txt

COPY . .
