FROM cgr.dev/chainguard/wolfi-base AS openssl-builder

RUN apk add --no-cache build-base perl curl ca-certificates linux-headers

RUN OPENSSL_VERSION=$(curl -fsSL "https://api.github.com/repos/openssl/openssl/releases?per_page=100" \
        | grep -o '"tag_name": *"openssl-[^"]*"' \
        | sed 's/.*openssl-\([^"]*\)".*/\1/' \
        | grep -E '^3\.[0-9]+\.[0-9]+$' \
        | sort -V \
        | tail -1) \
    && echo "Building OpenSSL ${OPENSSL_VERSION}" \
    && curl -fsSL "https://github.com/openssl/openssl/releases/download/openssl-${OPENSSL_VERSION}/openssl-${OPENSSL_VERSION}.tar.gz" | tar xz -C /tmp \
    && cd "/tmp/openssl-${OPENSSL_VERSION}" \
    && ./config --prefix=/usr/local --openssldir=/usr/local/etc/ssl --libdir=lib no-tests shared enable-ktls \
    && make -j"$(nproc)" \
    && make install_sw install_ssldirs \
    && rm -rf /tmp/openssl-*


FROM cgr.dev/chainguard/wolfi-base AS builder

WORKDIR /srv/website

COPY --from=openssl-builder /usr/local/lib /usr/local/lib
COPY --from=openssl-builder /usr/local/include/openssl /usr/local/include/openssl

RUN apk add --no-cache build-base python-3.12 python-3.12-dev git ca-certificates linux-headers

RUN ldconfig

ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
ENV CPPFLAGS="-I/usr/local/include"
ENV LDFLAGS="-L/usr/local/lib -Wl,-rpath,/usr/local/lib"
ENV LD_LIBRARY_PATH="/usr/local/lib"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev


FROM cgr.dev/chainguard/wolfi-base

WORKDIR /srv/website

RUN apk add --no-cache python-3.12 git ca-certificates

COPY --from=openssl-builder /usr/local/lib /usr/local/lib
COPY --from=openssl-builder /usr/local/etc/ssl /usr/local/etc/ssl
COPY --from=openssl-builder /usr/local/lib/libssl.so* /usr/lib/
COPY --from=openssl-builder /usr/local/lib/libcrypto.so* /usr/lib/

RUN ln -sf /etc/ssl/certs /usr/local/etc/ssl/certs
RUN ldconfig

COPY --from=builder /srv/website/.venv ./.venv
COPY src ./src

ENV PATH="/srv/website/.venv/bin:$PATH"
ENV LD_LIBRARY_PATH="/usr/local/lib"
ENV OPENSSL_CONF="/usr/local/etc/ssl/openssl.cnf"

CMD ["nercone-website"]
