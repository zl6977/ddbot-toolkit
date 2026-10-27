FROM ghcr.io/astral-sh/uv:0.11.11 AS uv
FROM python:3.12.12-slim-bookworm AS base
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl bash git ripgrep libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
FROM base AS build
ARG OMP_VERSION=18.13.2
ARG TARGETARCH=amd64
# Optional build-only CA; the build script creates this directory.
COPY docker/build-ca/ /usr/local/share/ca-certificates/
RUN update-ca-certificates
ENV UV_SYSTEM_CERTS=true
RUN set -eu; case "$TARGETARCH" in amd64) arch=x64;; arm64) arch=arm64;; *) exit 1;; esac; \
    base="https://github.com/can1357/oh-my-pi/releases/download/v$OMP_VERSION"; \
    cd /tmp; curl -fsSLO "$base/omp-linux-$arch"; curl -fsSLO "$base/SHA256SUMS.txt"; \
    grep " omp-linux-$arch$" SHA256SUMS.txt | sha256sum -c -; \
    mkdir -p /opt/ddbot/licenses; \
    curl -fsSL "$base/LICENSE" -o /opt/ddbot/licenses/OMP-LICENSE; \
    curl -fsSL "$base/THIRD-PARTY-NOTICES.txt" -o /opt/ddbot/licenses/OMP-THIRD-PARTY-NOTICES.txt; \
    install -m 755 "omp-linux-$arch" /usr/local/bin/omp; rm omp-linux-* SHA256SUMS.txt; omp --version
WORKDIR /workspace
COPY LICENSE /opt/ddbot/licenses/DDBOT-LICENSE
COPY model-dwis-config/ .agents/skills/model-dwis-config/
RUN mkdir -p /opt/ddbot && printf '%s\n' 'owlrl==7.6.2' 'rdflib==7.6.0' 'pyparsing==3.3.2' > /opt/ddbot/constraints.txt
ENV UV_CACHE_DIR=/workspace/.ddbot-runtime/uv-cache UV_PYTHON_DOWNLOADS=never UV_CONSTRAINT=/opt/ddbot/constraints.txt
RUN uv run .agents/skills/model-dwis-config/scripts/ddbot.py ontology pressure --limit 1 \
    && uv run .agents/skills/model-dwis-config/scripts/ddbot.py examples pressure --limit 1 \
    && uv run .agents/skills/model-dwis-config/scripts/manifest-creation/manifest_creation.py --help \
    && cp -a .ddbot-runtime /opt/ddbot/runtime-seed && rm -rf .ddbot-runtime
FROM base AS runtime
WORKDIR /workspace
COPY --from=build /usr/local/bin/omp /usr/local/bin/omp
COPY --from=build /workspace/.agents /workspace/.agents
COPY --from=build /opt/ddbot /opt/ddbot
ENV UV_CACHE_DIR=/workspace/.ddbot-runtime/uv-cache UV_PYTHON_DOWNLOADS=never UV_CONSTRAINT=/opt/ddbot/constraints.txt UV_SYSTEM_CERTS=true
COPY docker/entrypoint.sh /opt/ddbot/
RUN mkdir -p /workspace/input /workspace/output && chmod 1777 /workspace /workspace/output \
    && chmod -R a+rX /workspace/.agents /opt/ddbot \
    && chmod +x /opt/ddbot/*.sh
ENV UV_OFFLINE=true
USER 1000:1000
ENTRYPOINT ["/opt/ddbot/entrypoint.sh"]
