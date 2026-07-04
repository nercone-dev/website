FROM cgr.dev/chainguard/wolfi-base AS builder

WORKDIR /srv/website

ARG PACKAGES_VERSION

RUN apk add --no-cache git build-base linux-headers ca-certificates libffi openssl zlib bzip2 readline sqlite-libs ncurses xz

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ARG PYTHON_VERSION

ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python
RUN uv python install "${PYTHON_VERSION}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --python "${PYTHON_VERSION}"

COPY src ./src
RUN uv sync --frozen --no-dev --python "${PYTHON_VERSION}"


FROM cgr.dev/chainguard/wolfi-base

WORKDIR /srv/website

ARG PACKAGES_VERSION

RUN apk add --no-cache curl git ca-certificates libffi openssl zlib bzip2 readline sqlite-libs ncurses xz libstdc++

COPY --from=builder /opt/uv/python /opt/uv/python
COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/srv/website/.venv/bin:$PATH"

CMD ["nercone-website"]
