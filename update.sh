#!/usr/bin/env bash
set -e

echo "> UPDATE"

git pull

echo "> VERSION Python"

PYTHON_VERSION=$(curl -fsSL "https://api.github.com/repos/python/cpython/tags?per_page=100" \
    | grep -o '"name": *"v[^"]*"' \
    | sed 's/.*v\([^"]*\)".*/\1/' \
    | grep -E '^3\.13\.[0-9]+$' \
    | sort -V \
    | tail -1)

echo "Python ${PYTHON_VERSION}"

echo "> BUILD"

docker compose build --build-arg PYTHON_VERSION="${PYTHON_VERSION}"

echo "> START"

docker compose up -d
