from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Iterator

from rdflib import URIRef
from rdflib.namespace import XSD

from .ontology_lookup import DWISOntology
from .schemas import CheckResult, DWISConfigLine


_TYPE_LINE = re.compile(r"^[^\s:]+:[^\s:]+$")
_RELATION_LINE = re.compile(r"^[^\s:.=]+\s+[^\s:.=]+\s+[^\s:.=]+$")
_ATTRIBUTE_LINE = re.compile(r"^[^\s.=]+\.[^\s.=]+\s*=\s*.+$")
_INTEGER = re.compile(r"^[+-]?\d+$")
_NUMBER = re.compile(r"^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?$")
SUPPORTED_ATTRIBUTE_DATATYPES = {
    XSD.string, XSD.boolean, XSD.integer, XSD.int,
    XSD.decimal, XSD.float, XSD.double, XSD.dateTime,
}


def normalize_whitespace(dwis_config: str) -> Iterator[tuple[int, str]]:
    """Trim lines and remove blank lines (preprocessing rule 1)."""
    for line_number, raw_line in enumerate(dwis_config.splitlines(), 1):
        line = raw_line.strip()
        if line:
            yield line_number, line


def remove_full_line_comments(
    lines: Iterable[tuple[int, str]],
) -> Iterator[tuple[int, str]]:
    """Remove full-line comments while preserving inline hashes (rule 2)."""
    for line_number, line in lines:
        if not line.startswith("#"):
            yield line_number, line


def remove_trailing_semicolons(
    lines: Iterable[tuple[int, str]],
) -> Iterator[tuple[int, str]]:
    """Remove statement-ending semicolons outside quoted literals (rule 3)."""
    for line_number, line in lines:
        yield line_number, _remove_trailing_semicolon(line)


def remove_exact_duplicates(
    lines: Iterable[tuple[int, str]],
) -> Iterator[tuple[int, str]]:
    """Keep the first occurrence of each identical semantic line (rule 4)."""
    seen: set[str] = set()
    for line_number, line in lines:
        if line not in seen:
            seen.add(line)
            yield line_number, line


def preprocess_dwis_config_lines(dwis_config: str) -> Iterator[tuple[int, str]]:
    """Apply all deterministic-validation preprocessing repairs."""
    lines = normalize_whitespace(dwis_config)
    lines = remove_full_line_comments(lines)
    lines = remove_trailing_semicolons(lines)
    yield from remove_exact_duplicates(lines)


def _remove_trailing_semicolon(line: str) -> str:
    if not line.endswith(";"):
        return line

    in_quotes = False
    escaped = False
    for character in line[:-1]:
        if escaped:
            escaped = False
        elif character == "\\" and in_quotes:
            escaped = True
        elif character == '"':
            in_quotes = not in_quotes
    return line[:-1].rstrip() if not in_quotes else line


@dataclass
class DWISConfigCheckResult:
    lines: list[DWISConfigLine]
    is_valid: bool
    messages: list[str] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)


class DWISConfigChecker:
    """Apply the README construction rules, one method per named rule."""

    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def check(self, dwis_config: str) -> DWISConfigCheckResult:
        lines = self.config_lines(dwis_config)
        check_results = [
            self.check_non_empty_config(lines),
            self.check_line_type(lines),
            self.check_class_vocabulary(lines),
            self.check_instance_class_name_collision(lines),
            self.check_relation_vocabulary(lines),
            self.check_declared_relation_subject(lines),
            self.check_valid_relation_object(lines),
            self.check_declared_attribute_subject(lines),
            self.check_attribute_vocabulary(lines),
            self.check_attribute_range_compatibility(lines),
        ]
        messages = self._collect_messages(check_results)
        return DWISConfigCheckResult(
            lines=lines,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
            check_results=check_results,
        )

    def config_lines(self, dwis_config: str) -> list[DWISConfigLine]:
        return [
            DWISConfigLine(text=line, line_type=self._classify_line(line))
            for _, line in preprocess_dwis_config_lines(dwis_config)
        ]

    def check_non_empty_config(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages = [] if lines else [self._error("No DWIS config was generated.")]
        return self._check_result("non_empty_config", messages)

    def check_line_type(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages = [
            self._error(
                f"Line '{line.text}' does not match exactly one supported form: "
                "'Class:Instance', 'Subject ObjectProperty Object', or "
                "'Instance.DataProperty = Literal'."
            )
            for line in lines if line.line_type == "invalid"
        ]
        return self._check_result("line_type", messages)

    def check_class_vocabulary(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for line in self._lines_of_type(lines, "type"):
            class_name, instance_id = DWISConfigLine.split_type(line.text)
            if not self.ontology.is_subclass_of(class_name, "DWISNoun"):
                messages.append(self._error(
                    f"Class '{class_name}' for instance '{instance_id}' is not a DWISNoun subclass."
                ))
        return self._check_result("class_vocabulary", messages)

    def check_instance_class_name_collision(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for line in self._lines_of_type(lines, "type"):
            _, instance_id = DWISConfigLine.split_type(line.text)
            if self.ontology.get_class_uri(instance_id) is not None:
                messages.append(self._error(
                    f"Instance name '{instance_id}' conflicts with a DWIS class name."
                ))
        return self._check_result("instance_class_name_collision", messages)

    def check_relation_vocabulary(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for line in self._lines_of_type(lines, "relation"):
            subject, predicate, object_ = DWISConfigLine.split_relation(line.text)
            if not self.ontology.is_object_property(predicate):
                messages.append(self._error(
                    f"Predicate '{predicate}' in '{subject} {predicate} {object_}' "
                    "is not an ontology object property."
                ))
        return self._check_result("relation_vocabulary", messages)

    def check_declared_relation_subject(self, lines: list[DWISConfigLine]) -> CheckResult:
        declared = self._declared_instance_ids(lines)
        messages = [
            self._error(f"Relation subject '{subject}' is not a declared instance.")
            for line in self._lines_of_type(lines, "relation")
            for subject, _, _ in [DWISConfigLine.split_relation(line.text)]
            if subject not in declared
        ]
        return self._check_result("declared_relation_subject", messages)

    def check_valid_relation_object(self, lines: list[DWISConfigLine]) -> CheckResult:
        declared = self._declared_instance_ids(lines)
        messages = [
            self._error(
                f"Relation object '{object_}' is neither a declared instance nor a DWIS class name."
            )
            for line in self._lines_of_type(lines, "relation")
            for _, _, object_ in [DWISConfigLine.split_relation(line.text)]
            if object_ not in declared and self.ontology.resolve_class_name(object_) is None
        ]
        return self._check_result("valid_relation_object", messages)

    def check_declared_attribute_subject(self, lines: list[DWISConfigLine]) -> CheckResult:
        declared = self._declared_instance_ids(lines)
        messages = [
            self._error(f"Attribute subject '{subject}' is not a declared instance.")
            for line in self._lines_of_type(lines, "property")
            for subject, _, _ in [DWISConfigLine.split_property(line.text)]
            if subject not in declared
        ]
        return self._check_result("declared_attribute_subject", messages)

    def check_attribute_vocabulary(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for line in self._lines_of_type(lines, "property"):
            _, property_name, _ = DWISConfigLine.split_property(line.text)
            if not self.ontology.is_data_property(property_name):
                messages.append(self._error(
                    f"Attribute '{property_name}' is not an ontology datatype property."
                ))
        return self._check_result("attribute_vocabulary", messages)

    def check_attribute_range_compatibility(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for line in self._lines_of_type(lines, "property"):
            _, property_name, literal = DWISConfigLine.split_property(line.text)
            if not self.ontology.is_data_property(property_name):
                continue
            ranges = self.ontology.get_property_constraints(property_name)[1]
            compatible = select_compatible_attribute_datatype(literal, ranges)
            all_ranges_supported = bool(ranges) and all(
                datatype in SUPPORTED_ATTRIBUTE_DATATYPES for datatype in ranges
            )
            if compatible is None and all_ranges_supported:
                range_labels = ", ".join(
                    self._datatype_label(datatype) for datatype in ranges
                )
                messages.append(self._error(
                    f"Value '{literal}' cannot be unambiguously converted to any "
                    f"supported range of '{property_name}': [{range_labels}]."
                ))
        return self._check_result("attribute_range_compatibility", messages)

    @staticmethod
    def _classify_line(line: str) -> str:
        matches = [
            ("type", _TYPE_LINE.fullmatch(line) is not None),
            ("relation", _RELATION_LINE.fullmatch(line) is not None),
            ("property", _ATTRIBUTE_LINE.fullmatch(line) is not None),
        ]
        matched_types = [line_type for line_type, matched in matches if matched]
        return matched_types[0] if len(matched_types) == 1 else "invalid"

    @staticmethod
    def _lines_of_type(lines: list[DWISConfigLine], line_type: str) -> list[DWISConfigLine]:
        return [line for line in lines if line.line_type == line_type]

    @staticmethod
    def _declared_instance_ids(lines: list[DWISConfigLine]) -> set[str]:
        return {
            DWISConfigLine.split_type(line.text)[1]
            for line in lines if line.line_type == "type"
        }

    @staticmethod
    def _collect_messages(check_results: list[CheckResult]) -> list[str]:
        return [message for result in check_results for message in result.messages]

    @staticmethod
    def _check_result(rule_name: str, messages: list[str]) -> CheckResult:
        return CheckResult(
            rule_name=rule_name,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
        )

    @staticmethod
    def _datatype_label(datatype: URIRef) -> str:
        return f"xsd:{str(datatype).removeprefix(str(XSD))}"

    @staticmethod
    def _error(message: str) -> str:
        return f"[error][construction] {message}"


def normalize_attribute_literal(text: str, datatype: URIRef) -> str | None:
    """Apply the documented, unambiguous range-driven literal conversions."""
    scalar = _optional_quoted_scalar(text)
    if scalar is None:
        return None
    value, was_quoted = scalar

    if datatype == XSD.string:
        return json.dumps(value) if was_quoted else None
    if datatype == XSD.boolean:
        return value.lower() if value.lower() in {"true", "false"} else None
    if datatype in {XSD.integer, XSD.int}:
        return _normalize_integer(value) if _INTEGER.fullmatch(value) else None
    if datatype in {XSD.decimal, XSD.float, XSD.double}:
        return value if _NUMBER.fullmatch(value) else None
    if datatype == XSD.dateTime:
        try:
            if "T" not in value:
                return None
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return json.dumps(value)
        except ValueError:
            return None
    return None


def _normalize_integer(value: str) -> str:
    """Canonicalize an integer lexically without imposing Python's digit limit."""
    negative = value.startswith("-")
    digits = value.lstrip("+-").lstrip("0") or "0"
    return f"-{digits}" if negative and digits != "0" else digits


def select_compatible_attribute_datatype(
    text: str, ranges: Iterable[URIRef]
) -> URIRef | None:
    """Return the first supported range to which the literal can be converted."""
    for datatype in ranges:
        if (
            datatype in SUPPORTED_ATTRIBUTE_DATATYPES
            and normalize_attribute_literal(text, datatype) is not None
        ):
            return datatype
    return None


def _optional_quoted_scalar(text: str) -> tuple[str, bool] | None:
    if text.startswith('"') or text.endswith('"'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        return (value, True) if isinstance(value, str) else None
    return text, False
