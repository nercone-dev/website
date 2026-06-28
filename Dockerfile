FROM cgr.dev/chainguard/wolfi-base AS python-builder

ARG PYTHON_VERSION

RUN apk add --no-cache curl build-base linux-headers ca-certificates libffi-dev openssl-dev zlib-dev bzip2-dev readline-dev sqlite-dev ncurses-dev xz-dev

RUN curl -fsSL "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz" -o /tmp/cpython.tar.xz \
    && tar -xf /tmp/cpython.tar.xz -C /tmp \
    && cd /tmp/Python-${PYTHON_VERSION} \
    && ./configure \
        --prefix=/opt/python \
        --enable-optimizations \
        --with-lto \
        --with-ensurepip=install \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/cpython.tar.xz /tmp/Python-${PYTHON_VERSION}


FROM cgr.dev/chainguard/wolfi-base AS builder

WORKDIR /srv/website

RUN apk add --no-cache git build-base linux-headers ca-certificates libffi openssl zlib bzip2 readline sqlite-libs ncurses xz

COPY --from=python-builder /opt/python /opt/python

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PATH="/opt/python/bin:$PATH"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM cgr.dev/chainguard/wolfi-base

WORKDIR /srv/website

RUN apk add --no-cache curl git ca-certificates libffi openssl zlib bzip2 readline sqlite-libs ncurses xz libstdc++

COPY --from=python-builder /opt/python /opt/python
COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/opt/python/bin:/srv/website/.venv/bin:$PATH"

CMD ["nercone-website"]
