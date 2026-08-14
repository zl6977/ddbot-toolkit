# Installation

The repository contains one self-contained Skill at `model-dwis-config/`. That directory contains
the instructions, Python scripts, inline runtime dependencies, ontology, and shared example corpus.
Repository-only files such as `uv.lock`, tests, and maintenance docs remain outside the Skill
boundary. There is no generated release directory.

## Install for one user

Clone the repository to a development location, then symlink or copy its Skill directory into the
discovery directory used by the agent. For agents that use the portable `.agents/skills`
convention:

```bash
git clone <repository-url> <checkout>
ln -s <checkout>/model-dwis-config ~/.agents/skills/model-dwis-config
```

For Codex, the corresponding user-level location is normally
`~/.codex/skills/model-dwis-config`. Use the location configured by the target agent; do not install
both copies unless both discovery mechanisms are intentionally being tested.

The first CLI invocation lets uv create an isolated environment from the inline metadata in
`scripts/ddbot.py`. A restricted sandbox must provide writable uv cache storage and may need network
access during this first invocation; normal toolkit commands are local afterward. See the Skill's
[`references/environment.md`](../model-dwis-config/references/environment.md).

## Install for one repository

Clone, copy, or add the skill under the target repository:

```text
<repository>/.agents/skills/model-dwis-config/
```

A symlink to `<checkout>/model-dwis-config` is suitable for local development because edits in this
repository become visible to the target agent immediately. Restart the agent or start a new session
if it discovers Skills only at startup.

## Run the CLI

Invoke the bundled PEP 723 script from any working repository with:

```bash
uv run <skill-root>/scripts/ddbot.py <command>
```

When the sandbox's default uv cache is read-only, set `UV_CACHE_DIR` to a sandbox-writable cache
directory and retain that setting for every CLI invocation in the session. The Skill directory
itself may remain read-only.

For example:

```bash
uv run ~/.agents/skills/model-dwis-config/scripts/ddbot.py ontology "standpipe pressure"
```

## Release checklist

1. Run `uv lock --check` and commit the reviewed repository development lock file.
2. Run `uv run ruff check` and `uv run pytest`.
3. Validate `model-dwis-config/` with the Agent Skill validator.
4. Smoke-test a copy containing only `model-dwis-config/`, outside the development repository.
5. Create a Git tag or publish only the `model-dwis-config/` directory as the Skill archive.

The archive root must contain `SKILL.md` directly. Do not include the repository's `.git`, `docs`,
`tests`, `pyproject.toml`, or `uv.lock`.
