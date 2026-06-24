FROM cgr.dev/chainguard/wolfi-base AS builder

WORKDIR /srv/website

RUN apk add --no-cache build-base python-3.12 python-3.12-dev git ca-certificates linux-headers

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM cgr.dev/chainguard/wolfi-base

WORKDIR /srv/website

RUN apk add --no-cache python-3.12 git ca-certificates

COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/srv/website/.venv/bin:$PATH"

CMD ["nercone-website"]
