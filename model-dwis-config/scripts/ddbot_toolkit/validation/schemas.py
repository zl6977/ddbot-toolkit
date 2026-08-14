from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdflib import Graph


@dataclass(frozen=True)
class DWISConfigLine:
    text: str
    line_type: str

    @staticmethod
    def split_type(text: str) -> tuple[str, str]:
        """Parse 'Class:Instance' into (class_name, instance_id)."""
        class_name, instance_id = text.split(":", maxsplit=1)
        return class_name.strip(), instance_id.strip()

    @staticmethod
    def split_relation(text: str) -> tuple[str, str, str]:
        """Parse 'Subject Verb Object' into (subject_id, predicate_name, object_id)."""
        subject_id, predicate_name, object_id = text.split()
        return subject_id, predicate_name, object_id


@dataclass
class CheckResult:
    """Outcome of running a deterministic checker.

    ``is_valid`` is True when no ``[error]`` messages are produced.
    ``messages`` may contain ``[warning]`` entries even when ``is_valid`` is True.
    """

    rule_name: str
    is_valid: bool
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_name": self.rule_name,
            "is_valid": self.is_valid,
            "messages": self.messages,
        }


@dataclass
class DWISToRDFResult:
    graph: "Graph"
    turtle: str
    construction_valid: bool
    messages: list[str] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "construction_valid": self.construction_valid,
            "messages": self.messages,
            "check_results": [check.to_dict() for check in self.check_results],
        }


@dataclass
class ReasoningResult:
    """Outcome of running the OWL-RL reasoner over a sample's instance graph."""

    warnings: list[str] = field(default_factory=list)
    inferred_size_ratio: float = 1.0
    inferred_size_warning: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "warnings": self.warnings,
            "inferred_size_ratio": self.inferred_size_ratio,
            "inferred_size_warning": self.inferred_size_warning,
        }


@dataclass
class RDFDiagnosticResult:
    messages: list[str] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)
    disjointness_conflicts: list[str] = field(default_factory=list)
    functional_conflicts: list[str] = field(default_factory=list)
    connectivity_messages: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(message.startswith("[error]") for message in self.messages)

    def to_dict(self) -> dict[str, object]:
        return {
            "has_errors": self.has_errors,
            "messages": self.messages,
            "check_results": [check.to_dict() for check in self.check_results],
            "disjointness_conflicts": self.disjointness_conflicts,
            "functional_conflicts": self.functional_conflicts,
            "connectivity_messages": self.connectivity_messages,
        }
