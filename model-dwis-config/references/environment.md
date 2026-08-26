# Runtime environment

Use this reference once per agent session before the first DDBot Toolkit command. The checks cover
the execution capabilities the skill needs; they are not an installation tutorial.

## Required capabilities

- Execute local subprocesses and resolve `uv` on `PATH`.
- Run Python 3.11 or newer as required by `scripts/ddbot.py` inline metadata.
- Read `scripts/ddbot.py`, `assets/dwis-config-examples.jsonl`, and
  `assets/DWISVocabulary.ttl`.
- Write the cache used by `uv` and the directory selected for generated CONFIG files.
- Allow network access during the first `uv` invocation only if Python or script dependencies are
  not already cached. Ontology search, example retrieval, and validation are local after setup.

The skill does not require a plugin, MCP server, container runtime, elevated privileges, or network
access during normal execution.

## Preflight

First apply the filesystem-boundary and loader-derived path rules in `SKILL.md`. Do not use this
preflight to discover or repair paths. Set `<output-dir>` to the existing in-bound directory where
the CONFIG will be written and `<runtime-dir>` to an in-bound cache directory such as
`<cwd>/.ddbot-runtime`. Confirm canonical containment within `<cwd>` before running:

```bash
command -v uv
uv --version
test -r <loaded-skill-path>
test -r <script-path>
test -r <example-corpus-path>
test -r <ontology-path>
test -w <output-dir>
mkdir -p <runtime-dir>/uv-cache
test -w <runtime-dir>
UV_CACHE_DIR=<runtime-dir>/uv-cache uv run <script-path> --ontology <ontology-path> \
  ontology pressure --limit 1
UV_CACHE_DIR=<runtime-dir>/uv-cache uv run <script-path> examples pressure \
  --corpus <example-corpus-path> --limit 1
```

Treat the preflight as successful only when every command exits successfully and both DDBot
commands return JSON with at least one match. Keep using the same `UV_CACHE_DIR` for every later
`uv` command in the session. Do not rerun the preflight before every workflow step.

## Failure handling

- If `uv` is absent, report that it must be installed or exposed; do not silently replace the
  project environment with an unrelated Python interpreter.
- If the default uv cache is read-only, use the writable `UV_CACHE_DIR` above; do not treat that as
  a missing dependency or request broader filesystem access.
- If a complete compatible Python environment already contains the declared dependencies, it may
  run `<script-path>` directly after checking Python 3.11+, resource readability,
  output writability, and both smoke queries. Do not substitute an unrelated environment.
- If dependency or Python resolution still fails because the sandbox blocks network access, report
  the failed command and required capability. Do not run setup from another working directory.
- If loaded path metadata is absent, a derived resource is unreadable, or a path resolves outside
  `<cwd>`, report the exact condition and stop. Never search for a replacement.
- If `<output-dir>` is not writable, report that exact directory and stop. Do not select another
  directory, broaden permissions, or write outside `<cwd>`.
- If the script cannot import its bundled `ddbot_toolkit` modules, report the exact failure and stop;
  do not search for or install a second copy of the toolkit package.
- If either smoke query returns invalid JSON, an error object, or no matches, stop CLI-dependent
  work and report the command output. Do not continue generation or claim ontology grounding or
  validation.
