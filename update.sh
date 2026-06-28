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

echo "> VERSION Packages"

PACKAGE_NAMES=$(grep -oE 'apk add --no-cache .+' Dockerfile \
    | sed 's/apk add --no-cache //' \
    | tr ' ' '\n' \
    | grep -v '^$' \
    | sort -u)

PACKAGES_VERSION=$(curl -fsSL "https://packages.wolfi.dev/os/x86_64/APKINDEX.tar.gz" \
    | tar -xzO APKINDEX \
    | awk -v pkgs="$(echo "$PACKAGE_NAMES" | tr '\n' ':')" '
        BEGIN { n=split(pkgs, arr, ":"); for (i=1; i<=n; i++) if (arr[i] != "") wanted[arr[i]] = 1 }
        /^$/ { if (name in wanted) print name "=" ver ":" chk; name=""; ver=""; chk="" }
        /^P:/ { name=substr($0,3) }
        /^V:/ { ver=substr($0,3) }
        /^C:/ { chk=substr($0,3) }
        END { if (name in wanted) print name "=" ver ":" chk }
    ' \
    | sort \
    | sha256sum \
    | cut -d' ' -f1)

echo "Packages ${PACKAGES_VERSION}"

echo "> BUILD"

docker compose build \
    --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
    --build-arg PACKAGES_VERSION="${PACKAGES_VERSION}"

echo "> START"

docker compose up -d
