from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from rdflib import Graph


def iter_dwis_config_lines(dwis_config: str) -> Iterator[tuple[int, str]]:
    """Yield trimmed, nonblank, non-comment lines with source line numbers."""
    for line_number, raw_line in enumerate(dwis_config.splitlines(), 1):
        line = raw_line.strip()
        if line and not line.startswith("#"):
            yield line_number, line


@dataclass(frozen=True)
class DWISConfigLine:
    text: str
    line_type: str  # "type" | "relation" | "property" | "invalid"

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

    @staticmethod
    def split_property(text: str) -> tuple[str, str, str]:
        """Parse 'instance.property = literal' into (instance_id, property_name, literal).

        The literal keeps its quoting: a quoted string stays quoted so the
        caller can distinguish string vs. numeric literals.
        """
        subject, _, literal = text.partition("=")
        instance_id, _, property_name = subject.strip().partition(".")
        return instance_id.strip(), property_name.strip(), literal.strip()

    @staticmethod
    def is_property_line(text: str) -> bool:
        """True for 'instance.property = literal' lines."""
        # TImestamp literals might have :
        if "=" not in text or ":" in text.split("=")[0]:
            return False
        subject = text.split("=", 1)[0].strip()
        return subject.count(".") == 1 and all(subject.split("."))


@dataclass
class CheckResult:
    """Outcome of running a blocking deterministic rule.

    ``is_valid`` is True when no ``[error]`` messages are produced.
    Non-blocking observations are represented by ``DiagnosticResult`` instead.
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
class DiagnosticResult:
    """Outcome of a non-blocking deterministic diagnostic."""

    diagnostic_name: str
    triggered: bool
    messages: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "triggered": self.triggered,
            "messages": self.messages,
            **self.details,
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

    diagnostics: list[DiagnosticResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "diagnostics": {
                diagnostic.diagnostic_name: diagnostic.to_dict()
                for diagnostic in self.diagnostics
            },
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
