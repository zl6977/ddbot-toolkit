#!/bin/sh
set -eu
umask 077
export HOME="$(mktemp -d /tmp/ddbot-home.XXXXXX)"
if [ -n "${DDBOT_CA_CERT:-}" ]; then
    test -r "$DDBOT_CA_CERT" || { echo "CA certificate is not readable." >&2; exit 1; }
    openssl crl2pkcs7 -nocrl -certfile "$DDBOT_CA_CERT" -out /dev/null
    cat /etc/ssl/certs/ca-certificates.crt "$DDBOT_CA_CERT" > "$HOME/ca-bundle.pem"
    export SSL_CERT_FILE="$HOME/ca-bundle.pem"
    export CURL_CA_BUNDLE="$SSL_CERT_FILE" REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
    export NODE_EXTRA_CA_CERTS="$DDBOT_CA_CERT"
fi
export PI_CODING_AGENT_DIR="$HOME/.omp/agent"
mkdir -p "$PI_CODING_AGENT_DIR"
cd /workspace
test -w output || { echo "Output directory /workspace/output is not writable by $(id -u):$(id -g)." >&2; exit 1; }
if [ ! -d .ddbot-runtime ]; then
    cp -a /opt/ddbot/runtime-seed .ddbot-runtime
fi
test -w "$UV_CACHE_DIR" || { echo "Toolkit cache is not writable." >&2; exit 1; }
if [ "${1:-}" = "--container-smoke" ]; then
    test -r /workspace/.agents/skills/model-dwis-config/SKILL.md
    omp --version
    skill=/workspace/.agents/skills/model-dwis-config
    uv run "$skill/scripts/ddbot.py" ontology pressure --limit 1
    uv run "$skill/scripts/ddbot.py" examples pressure --corpus "$skill/assets/dwis-config-examples.jsonl" --limit 1
    uv run "$skill/scripts/manifest-creation/manifest_creation.py" --help
    touch /workspace/output/.container-smoke
    rm /workspace/output/.container-smoke
    exit 0
fi
test -r /run/omp-config/config.yml || { echo "Mount a configuration folder containing config.yml at /run/omp-config." >&2; exit 1; }
for file in config.yml models.yml; do
    if [ -f "/run/omp-config/$file" ]; then
        cp "/run/omp-config/$file" "$PI_CODING_AGENT_DIR/$file"
    fi
done
# Keep packaged behaviour separate from the user's provider/model settings.
cat > "$HOME/defaults.yml" <<'DEFAULTS'
skills:
  enabled: true
  enableSkillCommands: true
  customDirectories:
    - /workspace/.agents/skills
DEFAULTS
prompt=$(cat <<'PROMPT'
For DWIS modelling tasks, load model-dwis-config using the skill loader before acting and follow its workflow. The working directory is /workspace. Read user inputs from /workspace/input and write deliverables to /workspace/output. Keep toolkit caches in /workspace/.ddbot-runtime. In print mode, follow the skill's non-interactive workflow. Do not read provider credentials as task input.
PROMPT
)
exec omp --config "$HOME/defaults.yml" --append-system-prompt "$prompt" "$@"
