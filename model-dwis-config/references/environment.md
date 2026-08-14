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
  not already cached. Ontology search, motif retrieval, and validation are local after setup.

The skill does not require a plugin, MCP server, container runtime, elevated privileges, or network
access during normal execution.

## Preflight

Resolve `<skill-root>` as the directory containing `SKILL.md`, `<output-dir>` as the existing
directory where the requested CONFIG will be written, and `<runtime-dir>` as a sandbox-writable
temporary or cache directory. Use a persistent sandbox cache when available; otherwise create a
session directory with `mktemp -d`. Run:

```bash
command -v uv
uv --version
test -r <skill-root>/scripts/ddbot.py
test -r <skill-root>/assets/dwis-config-examples.jsonl
test -r <skill-root>/assets/DWISVocabulary.ttl
test -w <output-dir>
test -w <runtime-dir>
UV_CACHE_DIR=<runtime-dir>/uv-cache uv run <skill-root>/scripts/ddbot.py \
  ontology pressure --limit 1
UV_CACHE_DIR=<runtime-dir>/uv-cache uv run <skill-root>/scripts/ddbot.py motif pressure \
  --library <skill-root>/assets/dwis-config-examples.jsonl --limit 1
```

Treat the preflight as successful only when every command exits successfully and both DDBot
commands return JSON with at least one match. Keep using the same `UV_CACHE_DIR` for every later
`uv` command in the session. Do not rerun the preflight before every workflow step.

## Failure handling

- If `uv` is absent, ask the user to install or expose `uv`; do not silently replace the project
  environment with an unrelated Python interpreter.
- If the default uv cache is read-only, use the writable `UV_CACHE_DIR` above; do not treat that as
  a missing dependency or request broader filesystem access.
- If a complete compatible Python environment already contains the declared dependencies, it may
  run `<skill-root>/scripts/ddbot.py` directly after checking Python 3.11+, resource readability,
  output writability, and both smoke queries. Do not substitute an unrelated environment.
- If dependency or Python resolution still fails because the sandbox blocks network access,
  request that access or ask the user to prime the script environment with
  `uv run <skill-root>/scripts/ddbot.py --help` outside the restricted sandbox.
- If the skill files are unreadable, report the exact missing path and repair or reinstall the
  complete skill package before continuing.
- If `<output-dir>` is not writable, select a user-approved writable project directory. Do not
  broaden sandbox permissions or write outside the user's requested scope without approval.
- If the script cannot import its bundled `ddbot_toolkit` modules, repair or reinstall the complete
  Skill directory; do not install a second copy of the toolkit package.
- If either smoke query returns invalid JSON, an error object, or no matches, stop CLI-dependent
  work and report the command output. Collection and clarification may continue, but generation
  must not be presented as ontology-grounded or validated.
