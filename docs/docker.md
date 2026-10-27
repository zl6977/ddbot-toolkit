# OMP Docker image

The image includes OMP 18.13.2, Python, uv, and the complete modelling skill.
Only Docker is needed on the host. An administrator must supply the desired
model/provider settings and valid API credentials once.

## Build

Generic command (additional options are passed to Docker):

```text
[DDBOT_BUILD_CA=/path/to/ca.crt] [DDBOT_IMAGE=name:tag] bash /path/to/ddbot-toolkit/docker/build_docker.sh [docker build options]
```

Example from the repository root, without a custom CA:

```bash
bash docker/build_docker.sh
```

If your network requires a company CA for dependency downloads, set the
`DDBOT_BUILD_CA` environment variable to its external host path:

```bash
DDBOT_BUILD_CA="/path/to/company-ca.crt" bash /path/to/ddbot-toolkit/docker/build_docker.sh
```

Example on this Linux host, using the existing NORCE CA and host networking:

```bash
DDBOT_BUILD_CA="/usr/local/share/ca-certificates/Norwegian Research Centre Root CA.crt" \
  bash docker/build_docker.sh --network host
```

This build setting accepts a single public PEM certificate; do not copy it into
the repository. It is used only in the
builder stage, not copied into the final image. It remains in the local Docker
build cache; do not publish intermediate stages or export that cache if the
certificate should remain internal. Runtime trust still requires `--ca-cert`.
TLS verification remains enabled. Never pass a private key.

The default image tag is `ddbot-omp:local`. Set `DDBOT_IMAGE` to change it.
The script uses BuildKit when Buildx is available and otherwise falls back to
the legacy Docker builder. The script stages a temporary build context and
places the ignore rules at its root; it removes that directory on exit.
The Dockerfile and its ignore rules live in `docker/Dockerfile` and
`docker/Dockerfile.dockerignore`. The script selects that Dockerfile while
keeping the repository root as the build context so it can copy the skill.

Additional arguments pass to Docker, for example `--no-cache` or
`--build-arg OMP_VERSION=18.13.2`. Version overrides require revalidation.
The build verifies the OMP release checksum and resolves Python dependencies pinned
in the Dockerfile. The entrypoint contains the packaged skill defaults, prompt,
and offline smoke check.
The default target is Linux amd64; arm64 selection is available through BuildKit
but requires separate validation.

## Run

### Prepare the host folder

From the repository root:

```bash
mkdir -p dwis-work/config dwis-work/input dwis-work/output
cp docker/config-example/config.yml docker/config-example/models.yml dwis-work/config/
cp docker/config-example/provider.env.example dwis-work/config/provider.env
chmod 600 dwis-work/config/provider.env
```

Edit `config/config.yml` to select your provider/model and `config/provider.env`
to supply the API key. The example uses the built-in OpenAI provider and
`openai/gpt-4.1`; use a model your account supports. For another provider or
custom endpoint, edit `models.yml` using the
[OMP model schema](https://github.com/can1357/oh-my-pi/blob/v18.13.2/docs/models.md).
The `apiKey` value can name an environment variable defined in `provider.env`.
Do not commit your work folder or credentials.

Configuration is copied into a private disposable container home. Host
configuration and inputs are mounted read-only. Settings changes and session
history inside OMP disappear when the container exits. This interface supports
API keys; OAuth login and refresh persistence are not configured.

### Start OMP

Generic command:

```text
[DDBOT_IMAGE=name:tag] bash docker/run_docker.sh [--ca-cert /path/to/ca.crt] /path/to/work-folder [OMP arguments...]
```

After preparing the host folder and filling in its model/provider configuration,
start an interactive session from the repository root:

```bash
bash docker/run_docker.sh "$PWD/dwis-work"
```

Example using this host's NORCE CA (the certificate stays outside the repository):

```bash
bash docker/run_docker.sh \
  --ca-cert "/usr/local/share/ca-certificates/Norwegian Research Centre Root CA.crt" \
  "$PWD/dwis-work"
```

The runtime CA must be supplied again even when it was used during the build.


Ask OMP to generate or repair a DWIS CONFIG. The packaged instructions direct
deliverables to `/workspace/output`, which is `dwis-work/output` on the host.
You can explicitly invoke `/skill:model-dwis-config`.

For batch execution, provide a complete description and an explicit output path:

```bash
docker/run_docker.sh "$PWD/dwis-work" --print \
  'Use model-dwis-config in non-interactive mode. Generate a CONFIG for measured standpipe pressure. Validate and repair it, then save /workspace/output/standpipe.dwis.'
```

For the same batch task on the NORCE network:

```bash
bash docker/run_docker.sh \
  --ca-cert "/usr/local/share/ca-certificates/Norwegian Research Centre Root CA.crt" \
  "$PWD/dwis-work" --print \
  'Use model-dwis-config in non-interactive mode. Generate a CONFIG for measured standpipe pressure. Validate and repair it, then save /workspace/output/standpipe.dwis.'
```

The resulting file is `dwis-work/output/standpipe.dwis` on the host.
These runtime examples require working Docker networking; adding a CA does not
fix the disabled IPv4 forwarding described below.

Manifest conversion runs only when requested. Provider calls need network access.
Local ontology queries, retrieval, and validation use dependencies prepared in the
image. No host OMP, Python, or uv installation is needed.

The launcher uses your UID/GID so output belongs to you on Linux. Ensure the
host output directory is writable by that identity. Do not mount over
`/workspace`, because that hides the bundled skill. To use separate host folders,
adapt the launcher's three bind mounts. On Docker Desktop, enable sharing for the
chosen host folders.

## Offline smoke check

```bash
docker run --rm --network none ddbot-omp:local --container-smoke
```

This checks OMP startup, ontology/example queries, the converter CLI, and output
writability without provider credentials. It does not test a live model request.
The runtime cache and OMP home are disposable; only the mounted output persists.

## Build troubleshooting

If Docker reports disabled IPv4 forwarding and cannot download packages, fix the
Docker host networking or, on Linux, build with
`docker/build_docker.sh --network host`.

The company CA is optional and is not bundled in the final image. Mount a
public PEM CA certificate when running:

```bash
docker/run_docker.sh --ca-cert "/path/to/company-ca.crt" "$PWD/dwis-work"
```

The entrypoint combines it with the standard system roots in a temporary bundle
and configures curl, Python clients, uv, and OMP to use it. It runs without root
and leaves the host certificate unchanged. For direct Docker use, add
`--mount type=bind,src=/absolute/path/company-ca.crt,dst=/run/omp-ca.pem,readonly`
and `--env DDBOT_CA_CERT=/run/omp-ca.pem`.

Live provider generation, skill loader metadata, and Docker Desktop/arm64 still
require integration checks.
