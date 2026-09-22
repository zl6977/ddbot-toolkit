from __future__ import annotations

from itertools import combinations

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF
from rdflib.term import Node

from .ontology_lookup import INSTANCE_NS, DWISOntology
from .schemas import CheckResult, RDFDiagnosticResult


class RDFDiagnosticChecker:
    """Apply the README semantic rules, one method per named rule."""

    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def check(self, asserted_graph: Graph, inferred_graph: Graph | None = None) -> RDFDiagnosticResult:
        checks = [
            self.check_asserted_type_disjointness(asserted_graph),
            self.check_inferred_type_disjointness(asserted_graph, inferred_graph),
            self.check_asserted_graph_connectivity(asserted_graph),
            self.check_relation_domain_compatibility(asserted_graph),
            self.check_relation_range_compatibility(asserted_graph),
            self.check_functional_relation_conflict(asserted_graph),
            self.check_attribute_domain_compatibility(asserted_graph),
            self.check_functional_attribute_conflict(asserted_graph),
        ]
        result = RDFDiagnosticResult(check_results=checks)
        result.disjointness_conflicts = [
            message for check in checks[:2] for message in check.messages
        ]
        result.functional_conflicts = [
            message for check in checks
            if check.rule_name in {"functional_relation_conflict", "functional_attribute_conflict"}
            for message in check.messages
        ]
        result.connectivity_messages = checks[2].messages.copy()
        result.messages = [message for check in checks for message in check.messages]
        return result

    def check_asserted_type_disjointness(self, asserted_graph: Graph) -> CheckResult:
        return self._check_result(
            "asserted_type_disjointness",
            self._type_disjointness_messages(asserted_graph, label="asserted"),
        )

    def check_inferred_type_disjointness(
        self, asserted_graph: Graph, inferred_graph: Graph | None
    ) -> CheckResult:
        if inferred_graph is None:
            return self._check_result("inferred_type_disjointness", [])
        combined = self._copy_graph(asserted_graph)
        for triple in inferred_graph:
            combined.add(triple)
        return self._check_result(
            "inferred_type_disjointness",
            self._type_disjointness_messages(combined, label="inferred"),
        )

    def check_asserted_graph_connectivity(self, asserted_graph: Graph) -> CheckResult:
        is_connected, message = self._validate_connectivity(asserted_graph)
        messages = [] if is_connected else [self._error(message)]
        return self._check_result("asserted_graph_connectivity", messages)

    def check_relation_domain_compatibility(self, asserted_graph: Graph) -> CheckResult:
        messages = self._constraint_messages(
            asserted_graph, property_kind="object", endpoint="domain"
        )
        return self._check_result("relation_domain_compatibility", messages)

    def check_relation_range_compatibility(self, asserted_graph: Graph) -> CheckResult:
        messages = self._constraint_messages(
            asserted_graph, property_kind="object", endpoint="range"
        )
        return self._check_result("relation_range_compatibility", messages)

    def check_functional_relation_conflict(self, asserted_graph: Graph) -> CheckResult:
        messages = self._functional_conflict_messages(asserted_graph, property_kind="object")
        return self._check_result("functional_relation_conflict", messages)

    def check_attribute_domain_compatibility(self, asserted_graph: Graph) -> CheckResult:
        messages = self._constraint_messages(
            asserted_graph, property_kind="data", endpoint="domain"
        )
        return self._check_result("attribute_domain_compatibility", messages)

    def check_functional_attribute_conflict(self, asserted_graph: Graph) -> CheckResult:
        messages = self._functional_conflict_messages(asserted_graph, property_kind="data")
        return self._check_result("functional_attribute_conflict", messages)

    def _constraint_messages(
        self, graph: Graph, *, property_kind: str, endpoint: str
    ) -> list[str]:
        messages: list[str] = []
        constraint_index = 0 if endpoint == "domain" else 1
        for subject, predicate, object_ in graph:
            property_name = self.ontology.get_property_name(predicate)
            if property_name is None or not self._property_has_kind(property_name, property_kind):
                continue
            constraints = self.ontology.get_property_constraints(property_name)[constraint_index]
            node = subject if endpoint == "domain" else object_
            if self.ontology.node_matches_constraints(graph, node, constraints):
                continue
            labels = ", ".join(
                self.ontology.get_class_name(uri) or str(uri) for uri in constraints
            )
            messages.append(self._error(
                f"{property_kind} property '{property_name}' {endpoint} "
                f"'{self._instance_label(node)}' is incompatible with [{labels}]."
            ))
        return messages

    def _functional_conflict_messages(
        self, graph: Graph, *, property_kind: str
    ) -> list[str]:
        objects_by_key: dict[tuple[Node, URIRef], set[Node]] = {}
        for subject, predicate, object_ in graph:
            property_name = self.ontology.get_property_name(predicate)
            if (
                property_name is None
                or not self._property_has_kind(property_name, property_kind)
                or (predicate, RDF.type, OWL.FunctionalProperty) not in self.ontology.graph
            ):
                continue
            objects_by_key.setdefault((subject, predicate), set()).add(
                self._canonical_literal(object_)
            )

        messages: list[str] = []
        for (subject, predicate), objects in objects_by_key.items():
            if len(objects) <= 1:
                continue
            property_name = self.ontology.get_property_name(predicate) or str(predicate)
            values = ", ".join(sorted(self._instance_label(value) for value in objects))
            messages.append(self._error(
                f"Functional {property_kind} property conflict on "
                f"'{self._instance_label(subject)} {property_name}': [{values}]."
            ))
        return messages

    def _type_disjointness_messages(self, graph: Graph, *, label: str) -> list[str]:
        disjoint_pairs = self._disjoint_class_pairs()
        types_by_node: dict[Node, set[URIRef]] = {}
        for subject, _, class_uri in graph.triples((None, RDF.type, None)):
            if self._is_instance_node(subject) and isinstance(class_uri, URIRef):
                types_by_node.setdefault(subject, set()).add(class_uri)

        messages: list[str] = []
        for node, class_uris in types_by_node.items():
            for left, right in combinations(sorted(class_uris, key=str), 2):
                if frozenset((left, right)) not in disjoint_pairs:
                    continue
                messages.append(self._error(
                    f"{label} type disjointness conflict on '{self._instance_label(node)}': "
                    f"{self._class_label(left)} is disjoint with {self._class_label(right)}."
                ))
        return messages

    def _validate_connectivity(self, graph: Graph) -> tuple[bool, str]:
        instances: set[str] = set()
        edges: list[tuple[str, str]] = []
        for subject, predicate, object_ in graph:
            if not self._is_instance_node(subject):
                continue
            subject_label = self._instance_label(subject)
            instances.add(subject_label)
            if predicate == RDF.type or not self._is_instance_node(object_):
                continue
            object_label = self._instance_label(object_)
            instances.add(object_label)
            edges.append((subject_label, object_label))

        if len(instances) <= 1:
            return True, "Configuration graph is connected."
        adjacency = {instance: set() for instance in instances}
        for left, right in edges:
            adjacency[left].add(right)
            adjacency[right].add(left)
        remaining = set(instances)
        components: list[list[str]] = []
        while remaining:
            stack = [remaining.pop()]
            component: list[str] = []
            while stack:
                current = stack.pop()
                component.append(current)
                neighbours = adjacency[current] & remaining
                remaining.difference_update(neighbours)
                stack.extend(neighbours)
            components.append(sorted(component))
        if len(components) == 1:
            return True, "Configuration graph is connected."
        parts = [
            f"Component {index + 1}: [{', '.join(component)}]"
            for index, component in enumerate(sorted(components))
        ]
        return False, "Configuration has disconnected components:\n" + "\n".join(parts)

    def _disjoint_class_pairs(self) -> set[frozenset[URIRef]]:
        pairs: set[frozenset[URIRef]] = set()
        graph = self.ontology.graph
        for left, _, right in graph.triples((None, OWL.disjointWith, None)):
            if isinstance(left, URIRef) and isinstance(right, URIRef):
                pairs.add(frozenset((left, right)))
        for node in graph.subjects(RDF.type, OWL.AllDisjointClasses):
            members_node = graph.value(node, OWL.members)
            if members_node is None:
                continue
            try:
                members = [
                    member for member in Collection(graph, members_node)
                    if isinstance(member, URIRef)
                ]
            except Exception:
                continue
            for left, right in combinations(members, 2):
                pairs.add(frozenset((left, right)))
        return pairs

    def _property_has_kind(self, property_name: str, kind: str) -> bool:
        return (
            self.ontology.is_object_property(property_name)
            if kind == "object"
            else self.ontology.is_data_property(property_name)
        )

    def _class_label(self, class_uri: URIRef) -> str:
        return self.ontology.get_class_name(class_uri) or str(class_uri)

    @staticmethod
    def _is_instance_node(node: Node) -> bool:
        return isinstance(node, BNode) or (
            isinstance(node, URIRef) and str(node).startswith(INSTANCE_NS)
        )

    @staticmethod
    def _instance_label(node: Node) -> str:
        return str(node).removeprefix(INSTANCE_NS) if isinstance(node, URIRef) else str(node)

    @staticmethod
    def _canonical_literal(node: Node) -> Node:
        if not isinstance(node, Literal):
            return node
        try:
            value = node.toPython()
        except Exception:
            return node
        if isinstance(value, bool):
            return node
        if isinstance(value, (int, float)):
            number = float(value)
            return Literal(int(number) if number.is_integer() else number)
        return node

    @staticmethod
    def _copy_graph(graph: Graph) -> Graph:
        clone = Graph()
        for triple in graph:
            clone.add(triple)
        return clone

    @staticmethod
    def _error(message: str) -> str:
        return f"[error][semantic] {message}"

    @staticmethod
    def _check_result(rule_name: str, messages: list[str]) -> CheckResult:
        return CheckResult(
            rule_name=rule_name,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
        )
