FROM debian:bookworm-slim AS builder

WORKDIR /srv/website

ARG PACKAGES_VERSION

RUN apt update && apt install --no-install-recommends -y git build-essential ca-certificates curl libffi-dev libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libncurses-dev liblzma-dev && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ARG PYTHON_VERSION

ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python
RUN uv python install "${PYTHON_VERSION}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --python "${PYTHON_VERSION}"

COPY src ./src
RUN uv sync --frozen --no-dev --python "${PYTHON_VERSION}"


FROM gcr.io/distroless/base-debian12

WORKDIR /srv/website

ARG PACKAGES_VERSION

COPY src /srv/website/src

COPY --from=builder /opt/uv/python      /opt/uv/python
COPY --from=builder /srv/website/.venv  /srv/website/.venv

COPY --from=builder /etc/ssl/certs      /etc/ssl/certs
COPY --from=builder /etc/nsswitch.conf  /etc/nsswitch.conf

COPY --from=builder /usr/bin            /usr/bin
COPY --from=builder /usr/lib            /usr/lib
COPY --from=builder /usr/local/bin      /usr/local/bin
COPY --from=builder /usr/local/lib      /usr/local/lib
COPY --from=builder /usr/share/git-core /usr/share/git-core

ENV PATH="/srv/website/.venv/bin:/usr/local/bin:/usr/bin:$PATH"

CMD ["nercone-website"]
