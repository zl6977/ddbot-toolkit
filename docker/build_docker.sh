#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image="${DDBOT_IMAGE:-ddbot-omp:local}"
# Stage a context for both builders; company certificates stay out of source.
context_dir="$(mktemp -d)"
trap 'rm -rf -- "$context_dir"' EXIT
tar -C "$repo_dir" --exclude=__pycache__ --exclude='*.pyc' \
    --exclude=.venv --exclude=.ddbot-runtime \
    -cf - docker model-dwis-config LICENSE | tar -C "$context_dir" -xf -
cp "$repo_dir/docker/Dockerfile.dockerignore" "$context_dir/.dockerignore"
mkdir -p "$context_dir/docker/build-ca"
if [[ -n "${DDBOT_BUILD_CA:-}" ]]; then
    openssl x509 -in "$DDBOT_BUILD_CA" -out "$context_dir/docker/build-ca/custom.crt"
fi
if [[ "${DOCKER_BUILDKIT:-}" != 0 ]] && docker buildx version >/dev/null 2>&1; then
    export DOCKER_BUILDKIT=1
else
    export DOCKER_BUILDKIT=0
    echo "Using Docker's legacy builder (Buildx unavailable or disabled)." >&2
fi
docker build --file "$context_dir/docker/Dockerfile" --tag "$image" "$@" "$context_dir"
