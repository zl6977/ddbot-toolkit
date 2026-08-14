from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdflib import URIRef

from .paths import ontology_path
from .validation import DWISOntology

_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[^A-Za-z0-9]+")


def _terms(text: str) -> set[str]:
    return {part.casefold() for part in _WORD_BOUNDARY.split(text) if part}


@dataclass(frozen=True)
class OntologyMatch:
    name: str
    kind: str
    uri: str
    score: float
    comment: str | None
    parent: str | None
    domain: tuple[str, ...] = ()
    range: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "uri": self.uri,
            "score": self.score,
            "comment": self.comment,
            "parent": self.parent,
            "domain": list(self.domain),
            "range": list(self.range),
        }


class OntologySearch:
    """Search the bundled DWIS ontology without an embedding service."""

    def __init__(self, path: str | Path | None = None):
        self.ontology = DWISOntology(path or ontology_path())

    def search(self, query: str, *, kind: str = "all", limit: int = 10) -> list[OntologyMatch]:
        if kind not in {"all", "class", "property"}:
            raise ValueError("kind must be one of: all, class, property")
        query = query.strip()
        if not query:
            raise ValueError("query must not be blank")
        query_terms = _terms(query)
        query_folded = query.casefold()
        matches: list[OntologyMatch] = []

        if kind in {"all", "class"}:
            for name, data in self.ontology.classes.items():
                score = self._score(query_folded, query_terms, name, data.get("comment"))
                if score <= 0:
                    continue
                matches.append(
                    OntologyMatch(
                        name=name,
                        kind="class",
                        uri=str(data["uri"]),
                        score=score,
                        comment=data.get("comment"),
                        parent=self._label(data.get("superclass")),
                    )
                )

        if kind in {"all", "property"}:
            for name, data in self.ontology.properties.items():
                score = self._score(query_folded, query_terms, name, data.get("comment"))
                if score <= 0:
                    continue
                matches.append(
                    OntologyMatch(
                        name=name,
                        kind="property",
                        uri=str(data["uri"]),
                        score=score,
                        comment=data.get("comment"),
                        parent=self._label(data.get("superproperty")),
                        domain=tuple(filter(None, (self._label(v) for v in data.get("domain", [])))),
                        range=tuple(filter(None, (self._label(v) for v in data.get("range", [])))),
                    )
                )

        matches.sort(key=lambda item: (-item.score, item.kind, item.name))
        return matches[: max(0, limit)]

    @staticmethod
    def _score(query_folded: str, query_terms: set[str], name: str, comment: str | None) -> float:
        name_folded = name.casefold()
        name_terms = _terms(name)
        comment_terms = _terms(comment or "")
        score = 0.0
        if name_folded == query_folded:
            score += 100.0
        elif query_folded in name_folded:
            score += 30.0
        score += 8.0 * len(query_terms & name_terms)
        score += 1.0 * len(query_terms & comment_terms)
        return round(score, 3)

    def _label(self, uri: URIRef | None) -> str | None:
        if uri is None:
            return None
        return self.ontology.get_class_name(uri) or self.ontology.get_property_name(uri) or str(uri)

