#!/usr/bin/env bash
set -euo pipefail
ca_args=()
if [[ "${1:-}" == --ca-cert ]]; then
    [[ $# -ge 3 && -f "$2" && -r "$2" ]] || { echo "--ca-cert requires a readable PEM file and a work folder." >&2; exit 2; }
    ca_file="$(cd -- "$(dirname -- "$2")" && pwd)/$(basename -- "$2")"
    ca_args=(--mount "type=bind,src=$ca_file,dst=/run/omp-ca.pem,readonly" --env DDBOT_CA_CERT=/run/omp-ca.pem)
    shift 2
fi
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 [--ca-cert FILE] HOST_WORK_FOLDER [OMP arguments...]" >&2
    exit 2
fi
work_dir="$(cd -- "$1" && pwd)"
shift
mkdir -p "$work_dir/input" "$work_dir/output"
tty_args=()
if [[ -t 0 && -t 1 ]]; then tty_args=(-it); fi
env_args=()
if [[ -f "$work_dir/config/provider.env" ]]; then
    env_args=(--env-file "$work_dir/config/provider.env")
fi
exec docker run --rm "${tty_args[@]}" --user "$(id -u):$(id -g)" \
    "${env_args[@]}" "${ca_args[@]}" \
    --mount "type=bind,src=$work_dir/config,dst=/run/omp-config,readonly" \
    --mount "type=bind,src=$work_dir/input,dst=/workspace/input,readonly" \
    --mount "type=bind,src=$work_dir/output,dst=/workspace/output" \
    "${DDBOT_IMAGE:-ddbot-omp:local}" "$@"
