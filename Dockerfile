FROM cgr.dev/chainguard/wolfi-base AS builder

WORKDIR /srv/website

RUN apk add --no-cache git build-base linux-headers ca-certificates python-3.12 python-3.12-dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM cgr.dev/chainguard/wolfi-base

WORKDIR /srv/website

RUN apk add --no-cache curl git ca-certificates python-3.12

COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/srv/website/.venv/bin:$PATH"

CMD ["nercone-website"]
