#!/usr/bin/env bash
set -e

# Parse Arguments

COMPOSE=(docker compose)

for arg in "$@"; do
    case "${arg}" in
        --dev) COMPOSE+=(-f docker-compose.dev.yml) ;;
        *) echo "Unknown argument: ${arg}" >&2; exit 2 ;;
    esac
done

# Fetch Latest CPython 3.13.x Version

PYTHON_VERSION=$(curl -fsSL "https://api.github.com/repos/python/cpython/tags?per_page=100" \
    | grep -o '"name": *"v[^"]*"' \
    | sed 's/.*v\([^"]*\)".*/\1/' \
    | grep -E '^3\.13\.[0-9]+$' \
    | sort -V \
    | tail -1)

echo "Python ${PYTHON_VERSION}"

# Compute hashes of Debian's Package Repositories

MAIN_RELEASE=$(curl -fsSL "http://deb.debian.org/debian/dists/bookworm/Release")
MAIN_HASH=$(echo "${MAIN_RELEASE}" | awk '/^SHA256:/{in_sha=1; next} in_sha && / main\/binary-amd64\/Packages$/{print $1; exit}')

SECURITY_RELEASE=$(curl -fsSL "https://security.debian.org/debian-security/dists/bookworm-security/Release")
SECURITY_HASH=$(echo "${SECURITY_RELEASE}" | awk '/^SHA256:/{in_sha=1; next} in_sha && / main\/binary-amd64\/Packages$/{print $1; exit}')

PACKAGES_VERSION="${MAIN_HASH:0:16}-${SECURITY_HASH:0:16}"

echo "Debian Packages ${PACKAGES_VERSION}"
echo

# Build

echo "> BUILD"

"${COMPOSE[@]}" build \
    --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
    --build-arg PACKAGES_VERSION="${PACKAGES_VERSION}"

# Start

echo "> START"

"${COMPOSE[@]}" up -d
