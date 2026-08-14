from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .paths import motif_library_path

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value)}


@dataclass(frozen=True)
class MotifMatch:
    sample_id: str
    score: float
    description: str
    intent_sketch: tuple[str, ...]
    dwis_config: str
    lineage: str

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "score": self.score,
            "description": self.description,
            "intent_sketch": list(self.intent_sketch),
            "dwis_config": self.dwis_config,
            "lineage": self.lineage,
        }


class MotifRetriever:
    """Retrieve examples from the shared, leakage-safe example corpus."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or motif_library_path())
        self._records: list[dict[str, object]] | None = None
        self._document_frequency: Counter[str] | None = None

    def search(self, query: str, *, limit: int = 5) -> list[MotifMatch]:
        query_tokens = _tokens(query)
        if not query_tokens:
            raise ValueError("query must contain at least one searchable word")
        self._load()
        assert self._records is not None
        assert self._document_frequency is not None
        total = len(self._records)
        ranked: list[MotifMatch] = []
        for record in self._records:
            searchable = record["_searchable_tokens"]
            overlap = query_tokens & searchable
            if not overlap:
                continue
            score = sum(
                math.log((total + 1) / (self._document_frequency[token] + 1)) + 1
                for token in overlap
            )
            descriptions = record.get("descriptions") or []
            ranked.append(
                MotifMatch(
                    sample_id=str(record["sample_id"]),
                    score=round(score, 4),
                    description=str(descriptions[0]) if descriptions else "",
                    intent_sketch=tuple(str(v) for v in record.get("intent_sketch") or []),
                    dwis_config=str(record["dwis_config"]),
                    lineage=str(record.get("lineage", "")),
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.sample_id))
        return ranked[: max(0, limit)]

    def _load(self) -> None:
        if self._records is not None:
            return
        records: list[dict[str, object]] = []
        frequencies: Counter[str] = Counter()
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid motif JSONL at line {line_number}: {exc}") from exc
                searchable_text = " ".join(
                    [
                        *(str(v) for v in record.get("descriptions") or []),
                        *(str(v) for v in record.get("intent_sketch") or []),
                        str(record.get("dwis_config", "")),
                    ]
                )
                searchable_tokens = _tokens(searchable_text)
                record["_searchable_tokens"] = searchable_tokens
                records.append(record)
                frequencies.update(searchable_tokens)
        self._records = records
        self._document_frequency = frequencies
