# Docker packaging plan: OMP with model-dwis-config

Status: proposed; this document does not implement or publish an image.

## Intended experience

Ship OMP, the complete `model-dwis-config` skill, and its Python runtime in one
image. Users need Docker and a supplied provider/model configuration, but do not
install OMP, Python, uv, or the skill themselves. Provider credentials and model
selection remain outside the image. Generated files persist on the host.

Recommend one host parent folder with separate configuration, input, and output
subdirectories. Mount those subdirectories separately so configuration can be
read-only without making output read-only:

```text
dwis-work/
  config/       provider settings, model selection, credentials
  input/        optional descriptions and existing CONFIG files
  output/       generated .dwis files and requested manifest JSON
```

The same container interface also supports unrelated host directories by changing
the mount sources. Do not require configuration and output to share a directory.

## Container layout

| Container path | Source and purpose |
| --- | --- |
| `/workspace/.agents/skills/model-dwis-config/` | Complete skill baked into image |
| `/workspace/input/` | Host input mount, read-only |
| `/workspace/output/` | Host output mount, writable |
| `/workspace/.ddbot-runtime/` | Writable, disposable toolkit runtime/cache |
| `/run/omp-config/` | Host configuration mount, read-only |
| Writable container home | OMP runtime settings and session state |

Set the working directory to `/workspace`. Do not mount over that whole directory:
a whole-workspace bind mount would hide the bundled skill.

The skill requires its canonical path, ontology, examples, cache, inputs, and
outputs to be inside the working directory. Installing it only in a global home
or linking it to a location outside `/workspace` would violate that rule. Keep
its actual files under `/workspace` and verify that OMP supplies the resolved
`SKILL.md` path when loading it. OMP itself consumes configuration outside the
workspace; the modelling skill does not need to read credentials.

## Image build

1. Select and pin a tested OMP release and a glibc-based Linux base image. Prefer
   the upstream release binary, verified by checksum, to avoid a build toolchain
   in the final image. Confirm its runtime libraries on the selected base.
2. Install pinned uv and Python 3.11 or newer, plus the shell/tools OMP needs.
3. Copy the entire skill directory, including bundled manifest conversion and
   licenses. Exclude repository development caches, virtual environments, test
   data, Git history, and all user configuration using `.dockerignore`.
4. Resolve and lock the script dependencies during build. Prepare the exact
   environment used by the skill's documented `uv run` commands, including the
   optional converter. Preserve cache paths or seed the writable runtime cache
   on startup. Prove this works without downloads with networking disabled;
   merely installing dependencies in an unrelated virtual environment is insufficient.
5. Run ontology and example smoke queries during build. Record OMP, Python, uv,
   skill revision, and dependency versions in image metadata.

Start with Linux amd64; add arm64 only after the selected release and native
runtime have passed the same checks on that architecture.

## External configuration and startup

Provide a commented template and a launcher so an administrator can prepare the
folder once and distribute it. Users still need valid provider access; packaging
cannot supply credentials or choose an organization-specific endpoint implicitly.

Before implementation, verify the pinned OMP release's settings schema, provider
and model registry format, authentication storage, configuration directory
controls, and non-interactive flags. Use OMP-native formats instead of introducing
a second provider schema. Document concrete filenames and a working provider
example once verified; do not assume all settings fit in one JSON file.

The entrypoint should:

1. Check required configuration files and writable output/cache locations, with
   actionable errors that do not print credentials.
2. Stage the read-only host configuration into a private writable OMP home if OMP
   needs to update its settings or auth storage. Never overwrite host originals.
   OAuth refresh persistence is outside the initial API-key-based scope.
3. Apply packaged defaults for skill discovery and skill commands while preserving
   the supplied provider and model. Fail clearly on conflicting settings that
   disable the bundled skill.
4. Initialize the prepared runtime cache without package downloads.
5. Start OMP from `/workspace` using `exec`, preserving arguments, signals, and exit
   codes. Supply a small instruction directing deliverables to `/workspace/output`
   and explicitly loading `model-dwis-config` for modelling tasks.

Run as a non-root user. Support a host UID/GID override and ensure writable home
and runtime directories also work with that override. Do not solve host output
permissions by recursively changing ownership of mounted directories.

Session history is disposable initially. If persistence is later needed, expose
a separate state mount; do not mix sessions or copied credentials with deliverables.

## Proposed invocation

These commands describe the intended interface; the image and entrypoint are
not yet implemented. Populate `config/` using the future documented template.

```bash
mkdir -p dwis-work/config dwis-work/input dwis-work/output
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD/dwis-work/config,dst=/run/omp-config,readonly" \
  --mount "type=bind,src=$PWD/dwis-work/input,dst=/workspace/input,readonly" \
  --mount "type=bind,src=$PWD/dwis-work/output,dst=/workspace/output" \
  ddbot-omp:<version>
```

The interactive session should discover the skill immediately. Users can ask it
to generate or repair a CONFIG and find the result in `dwis-work/output/`.
Provide a second launcher example for batch mode after checking the selected
OMP flags. Its prompt must explicitly request non-interactive operation, load
the skill, and name the output file. The skill defaults to interactive questions.
Provider requests require network access; local toolkit operations should not.

## Implementation deliverables

- `Dockerfile` and `.dockerignore`.
- `docker/entrypoint.sh`, configuration examples, and packaged agent defaults.
- A launcher or Compose file implementing the mounts and runtime identity.
- `docs/docker.md` with build/run, provider setup, interactive and batch examples,
  output retrieval, and permission troubleshooting; link it from the README.
- Container smoke checks and a build workflow. Publishing to a registry is a
  separate release step, with registry and version tags selected at that time.

## Acceptance checks

- A fresh host with Docker and prepared configuration can start OMP without local
  language runtimes or skill installation.
- OMP discovers the bundled skill and supplies valid resolved-path metadata.
- With networking disabled, documented toolkit preflight, validation, and optional
  manifest conversion succeed using the prepared dependencies.
- With test provider credentials, interactive and explicit batch requests produce
  validated CONFIG files in the host output directory; optional conversion writes
  a separate JSON file only when requested.
- Files survive `--rm` and are usable by the host user. Test default identity and
  UID/GID override, mounted paths with spaces, and Docker Desktop behavior.
- Missing or invalid configuration, provider failures, and unwritable output
  produce clear failures; cancellation and OMP exit status propagate correctly.
- Replacing host provider/model configuration takes effect on the next launch
  without rebuilding. Input and configuration mounts remain unchanged.
- Image layers and build logs contain no credentials or local user state.

## References and implementation checkpoints

Repository constraints come from `model-dwis-config/SKILL.md` and
`model-dwis-config/references/environment.md`.

Upstream [OMP installation instructions](https://github.com/can1357/oh-my-pi#install)
describe pinned binary installation. Its [skill documentation](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)
describes project discovery, skill loading, and command settings. These were
reviewed while planning; recheck against the exact pinned release before writing
configuration templates and final CLI examples.
