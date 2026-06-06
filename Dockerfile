FROM python:3.12-slim-trixie AS builder

WORKDIR /srv/website

RUN apt-get update && apt-get install -y --no-install-recommends git build-essential libssl-dev && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM python:3.12-slim-trixie

WORKDIR /srv/website

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/srv/website/.venv/bin:$PATH"
CMD ["nercone-website"]
