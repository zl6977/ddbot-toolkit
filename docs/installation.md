# Installation

The repository contains one self-contained Skill at `model-dwis-config/`. That directory contains
the instructions, Python scripts, inline runtime dependencies, ontology, and shared example corpus.
Repository-only files such as `uv.lock`, tests, and maintenance docs remain outside the Skill
boundary. There is no generated release directory.

## Install for one repository

Copy, vendor, or add the Skill under the target repository:

```text
<repository>/.agents/skills/model-dwis-config/
```

The Skill treats the host working directory as its filesystem boundary. Its loader-resolved
`SKILL.md`, bundled scripts, ontology, examples, runtime cache, CONFIG inputs, and outputs must all
resolve inside that directory. Do not use a user-level installation or a symlink whose canonical
target is outside the repository; copy or vendor the Skill instead.

The first CLI invocation lets uv create an isolated environment from the inline metadata in
`scripts/ddbot.py`. Keep the uv cache inside the working directory. The first invocation may need
network access; normal toolkit commands are local afterward. See the Skill's
[`references/environment.md`](../model-dwis-config/references/environment.md).

## Run the CLI

Derive the bundled PEP 723 script path from Skill loader metadata and invoke it from the containing
working directory with:

```bash
uv run <script-path> <command>
```

Set `UV_CACHE_DIR` to a writable cache contained within the same working directory and retain that
setting for every CLI invocation in the session. The Skill directory itself may remain read-only.

For example, when the loader selected the project-local Skill:

```bash
uv run <repository>/.agents/skills/model-dwis-config/scripts/ddbot.py ontology \
  "standpipe pressure"
```

## Release checklist

1. Run `uv lock --check` and commit the reviewed repository development lock file.
2. Run `uv run ruff check` and `uv run pytest`.
3. Validate `model-dwis-config/` with the Agent Skill validator.
4. Smoke-test a copy containing only `model-dwis-config/`, outside the development repository.
5. Create a Git tag or publish only the `model-dwis-config/` directory as the Skill archive.

The archive root must contain `SKILL.md` directly. Do not include the repository's `.git`, `docs`,
`tests`, `pyproject.toml`, or `uv.lock`.
