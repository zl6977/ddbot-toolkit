from __future__ import annotations

import os
from pathlib import Path


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def ontology_path() -> Path:
    override = os.environ.get("DDBOT_ONTOLOGY_PATH")
    if override:
        return Path(override)
    return skill_root() / "assets" / "DWISVocabulary.ttl"


def motif_library_path() -> Path:
    override = os.environ.get("DDBOT_MOTIF_LIBRARY_PATH")
    if override:
        return Path(override)
    return skill_root() / "assets" / "dwis-config-examples.jsonl"
