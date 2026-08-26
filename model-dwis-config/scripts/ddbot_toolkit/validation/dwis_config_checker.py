from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import URIRef

from .ontology_lookup import DWISOntology
from .schemas import CheckResult, DWISConfigLine


@dataclass
class DWISConfigCheckResult:
    lines: list[DWISConfigLine]
    is_valid: bool
    messages: list[str] = field(default_factory=list)
    check_results: list[CheckResult] = field(default_factory=list)


class DWISConfigChecker:
    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def check(self, dwis_config: str) -> DWISConfigCheckResult:
        lines = self.config_lines(dwis_config)
        check_results = [
            self.check_non_empty_config(lines),
            self.check_type_declaration_syntax(lines),
            self.check_relation_syntax(lines),
        ]
        messages = self._collect_failed_messages(check_results)
        if messages:
            return DWISConfigCheckResult(
                lines=lines,
                is_valid=False,
                messages=messages,
                check_results=check_results,
            )

        check_results.extend(
            [
                self.check_class_vocabulary(lines),
                self.check_verb_vocabulary(lines),
                self.check_declared_relation_endpoints(lines),
                self.check_instance_class_name_collision(lines),
                self.check_duplicate_type_declaration(lines),
                self.check_object_property(lines),
            ]
        )
        messages = self._collect_failed_messages(check_results)
        return DWISConfigCheckResult(
            lines=lines,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
            check_results=check_results,
        )

    def config_lines(self, dwis_config: str) -> list[DWISConfigLine]:
        lines: list[DWISConfigLine] = []
        for raw_line in dwis_config.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("dwis ") or line.startswith("#"):
                continue
            line_type = "type" if ":" in line else "relation"
            lines.append(DWISConfigLine(text=line, line_type=line_type))
        return lines

    def check_non_empty_config(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages = [] if lines else [self._error("parsing", "No DWIS config was generated.")]
        return self._check_result("non_empty_config", messages)

    def check_type_declaration_syntax(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type == "type":
                self._check_type_declaration_syntax(config_line.text, messages)
        return self._check_result("type_declaration_syntax", messages)

    def check_relation_syntax(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type == "relation":
                self._check_relation_declaration_syntax(config_line.text, messages)
        return self._check_result("relation_syntax", messages)

    def check_class_vocabulary(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type != "type":
                continue
            class_name, instance_id = DWISConfigLine.split_type(config_line.text)
            self._check_class_vocabulary(class_name, instance_id, messages)
        return self._check_result("class_vocabulary", messages)

    def check_verb_vocabulary(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type != "relation":
                continue
            subject_id, predicate_name, object_id = DWISConfigLine.split_relation(config_line.text)
            self._check_verb_vocabulary(subject_id, predicate_name, object_id, messages)
        return self._check_result("verb_vocabulary", messages)

    def check_declared_relation_endpoints(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        declared_instances = self._declared_instance_ids(lines)
        for config_line in lines:
            if config_line.line_type != "relation":
                continue
            subject_id, _, object_id = DWISConfigLine.split_relation(config_line.text)
            if subject_id not in declared_instances:
                messages.append(self._error("parsing", f"Relation subject '{subject_id}' is not a declared instance."))
            if object_id not in declared_instances and self.ontology.resolve_class_name(object_id) is None:
                messages.append(
                    self._error(
                        "parsing",
                        f"Relation object '{object_id}' is neither a declared instance nor a DWIS class name.",
                    )
                )
        return self._check_result("declared_relation_endpoints", messages)

    def check_instance_class_name_collision(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type != "type":
                continue
            _, instance_id = DWISConfigLine.split_type(config_line.text)
            self._check_instance_name_is_not_class_name(instance_id, messages)
        return self._check_result("instance_class_name_collision", messages)

    def check_duplicate_type_declaration(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        declared_pairs: set[tuple[str, str]] = set()
        for config_line in lines:
            if config_line.line_type != "type":
                continue
            class_name, instance_id = DWISConfigLine.split_type(config_line.text)
            self._check_duplicate_type_declaration(class_name, instance_id, declared_pairs, messages)
        return self._check_result("duplicate_type_declaration", messages)

    def check_object_property(self, lines: list[DWISConfigLine]) -> CheckResult:
        messages: list[str] = []
        for config_line in lines:
            if config_line.line_type != "relation":
                continue
            _, predicate_name, _ = DWISConfigLine.split_relation(config_line.text)
            if self.ontology.get_property_uri(predicate_name) is None:
                continue
            self._check_verb_is_object_property(predicate_name, messages)
        return self._check_result("object_property", messages)

    def _check_type_declaration_syntax(self, line: str, messages: list[str]) -> tuple[str, str] | None:
        parts = line.split(":")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            messages.append(self._error("parsing", f"Invalid type declaration '{line}'. Expected 'Class:Instance'."))
            return None
        return DWISConfigLine.split_type(line)

    def _check_relation_declaration_syntax(self, line: str, messages: list[str]) -> tuple[str, str, str] | None:
        parts = line.split()
        if len(parts) != 3:
            messages.append(self._error("parsing", f"Could not parse relation line '{line}'. Expected 'Subject Verb Object'."))
            return None
        return parts[0], parts[1], parts[2]

    def _check_class_vocabulary(self, class_name: str, instance_id: str, messages: list[str]) -> URIRef | None:
        class_uri = self.ontology.get_class_uri(class_name)
        if class_uri is None:
            messages.append(self._error("parsing", f"Unknown class '{class_name}' for instance '{instance_id}'."))
            return None
        if not self.ontology.is_subclass_of(class_name, "DWISNoun"):
            messages.append(self._error("parsing", f"Class '{class_name}' is not a subclass of DWISNoun."))
            return None
        return class_uri

    def _check_verb_vocabulary(
        self,
        subject_id: str,
        predicate_name: str,
        object_id: str,
        messages: list[str],
    ) -> URIRef | None:
        predicate_uri = self.ontology.get_property_uri(predicate_name)
        if predicate_uri is None:
            messages.append(
                self._error(
                    "parsing",
                    f"Unknown predicate '{predicate_name}' for triple '{subject_id} {predicate_name} {object_id}'.",
                )
            )
            return None
        return predicate_uri

    def _check_verb_is_object_property(self, predicate_name: str, messages: list[str]) -> bool:
        if self.ontology.is_object_property(predicate_name):
            return True
        messages.append(self._error("parsing", f"Predicate '{predicate_name}' is not an ontology object property."))
        return False

    def _check_duplicate_type_declaration(
        self,
        class_name: str,
        instance_id: str,
        declared_pairs: set[tuple[str, str]],
        messages: list[str],
    ) -> bool:
        pair = (class_name, instance_id)
        if pair not in declared_pairs:
            declared_pairs.add(pair)
            return True
        messages.append(self._error("parsing", f"Duplicate declaration '{class_name}:{instance_id}'."))
        return False

    def _check_instance_name_is_not_class_name(self, instance_id: str, messages: list[str]) -> bool:
        if self.ontology.get_class_uri(instance_id) is None:
            return True
        messages.append(self._error("parsing", f"Instance name '{instance_id}' conflicts with a DWIS class name."))
        return False

    def _declared_instance_ids(self, lines: list[DWISConfigLine]) -> set[str]:
        return {
            DWISConfigLine.split_type(config_line.text)[1]
            for config_line in lines
            if config_line.line_type == "type"
        }


    @staticmethod
    def _collect_failed_messages(check_results: list[CheckResult]) -> list[str]:
        messages: list[str] = []
        for check in check_results:
            messages.extend(check.messages)
        return messages

    @staticmethod
    def _check_result(rule_name: str, messages: list[str]) -> CheckResult:
        return CheckResult(
            rule_name=rule_name,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
        )

    @staticmethod
    def _error(category: str, message: str) -> str:
        return f"[error][{category}] {message}"
