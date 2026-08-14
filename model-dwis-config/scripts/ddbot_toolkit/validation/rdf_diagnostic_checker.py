from __future__ import annotations

from itertools import combinations

from rdflib import BNode, Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF
from rdflib.term import Node

from .ontology_lookup import INSTANCE_NS, DWISOntology
from .schemas import CheckResult, RDFDiagnosticResult


class RDFDiagnosticChecker:
    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def check(self, asserted_graph: Graph, inferred_graph: Graph | None = None) -> RDFDiagnosticResult:
        result = RDFDiagnosticResult()

        asserted_disjointness = self.check_asserted_type_disjointness(asserted_graph)
        inferred_disjointness = self.check_inferred_type_disjointness(asserted_graph, inferred_graph)
        functional_conflicts = self.check_functional_property_conflicts(asserted_graph, inferred_graph)
        connectivity = self.check_connectivity(asserted_graph)

        result.check_results.extend(
            [
                asserted_disjointness,
                inferred_disjointness,
                functional_conflicts,
                connectivity,
            ]
        )

        result.disjointness_conflicts.extend(asserted_disjointness.messages)
        result.disjointness_conflicts.extend(inferred_disjointness.messages)
        result.functional_conflicts.extend(functional_conflicts.messages)
        result.connectivity_messages.extend(connectivity.messages)

        result.messages.extend(result.disjointness_conflicts)
        result.messages.extend(result.functional_conflicts)
        result.messages.extend(result.connectivity_messages)
        return result

    def check_asserted_type_disjointness(self, asserted_graph: Graph) -> CheckResult:
        messages = self._check_type_disjointness(asserted_graph, label="asserted")
        return self._check_result("asserted_type_disjointness", messages)

    def check_inferred_type_disjointness(
        self,
        asserted_graph: Graph,
        inferred_graph: Graph | None,
    ) -> CheckResult:
        if inferred_graph is None:
            return self._check_result("inferred_type_disjointness", [])

        combined = Graph()
        for triple in asserted_graph:
            combined.add(triple)
        for triple in inferred_graph:
            combined.add(triple)
        messages = self._check_type_disjointness(combined, label="inferred")
        return self._check_result("inferred_type_disjointness", messages)

    def check_functional_property_conflicts(
        self,
        asserted_graph: Graph,
        inferred_graph: Graph | None,
    ) -> CheckResult:
        messages = self._check_functional_property_conflicts(asserted_graph, label="asserted")
        if inferred_graph is not None:
            messages.extend(self._check_functional_property_conflicts(inferred_graph, label="inferred"))
        return self._check_result("functional_property_conflicts", messages)

    def check_connectivity(self, asserted_graph: Graph) -> CheckResult:
        messages = self._check_connectivity(asserted_graph)
        return self._check_result("asserted_graph_connectivity", messages)

    def _check_type_disjointness(self, graph: Graph, *, label: str) -> list[str]:
        messages: list[str] = []
        disjoint_pairs = self._disjoint_class_pairs()
        if not disjoint_pairs:
            return messages

        types_by_node: dict[Node, set[URIRef]] = {}
        for subj, _, class_uri in graph.triples((None, RDF.type, None)):
            if self._is_instance_node(subj) and isinstance(class_uri, URIRef):
                types_by_node.setdefault(subj, set()).add(class_uri)

        for node, class_uris in types_by_node.items():
            for left, right in combinations(sorted(class_uris, key=str), 2):
                pair = frozenset((left, right))
                if pair not in disjoint_pairs:
                    continue
                messages.append(
                    self._error(
                        "semantic",
                        f"{label} type disjointness conflict on '{self._instance_label(node)}': "
                        f"{self._class_label(left)} is disjoint with {self._class_label(right)}.",
                    )
                )
        return messages

    def _check_functional_property_conflicts(self, graph: Graph, *, label: str) -> list[str]:
        messages: list[str] = []
        functional_properties = self._functional_properties()
        if not functional_properties:
            return messages

        objects_by_subject_property: dict[tuple[Node, URIRef], set[Node]] = {}
        for subj, pred, obj in graph:
            if pred not in functional_properties or not self._is_instance_node(subj):
                continue
            objects_by_subject_property.setdefault((subj, pred), set()).add(obj)

        for (subj, pred), objects in objects_by_subject_property.items():
            if len(objects) <= 1:
                continue
            object_labels = ", ".join(sorted(self._instance_label(obj) for obj in objects))
            messages.append(
                self._error(
                    "semantic",
                    f"{label} functional property conflict on '{self._instance_label(subj)} "
                    f"{self._property_label(pred)}': multiple objects [{object_labels}].",
                )
            )
        return messages

    def _check_connectivity(self, graph: Graph) -> list[str]:
        is_connected, message = self._validate_connectivity(graph)
        if is_connected:
            return []
        return [self._error("structural", message)]

    def _validate_connectivity(self, graph: Graph) -> tuple[bool, str]:
        instances = set()
        edges: list[tuple[str, str]] = []

        for subj, pred, obj in graph:
            if not self._is_instance_node(subj):
                continue
            subj_label = self._instance_label(subj)
            instances.add(subj_label)
            if pred == RDF.type or not self._is_instance_node(obj):
                continue
            obj_label = self._instance_label(obj)
            instances.add(obj_label)
            edges.append((subj_label, obj_label))

        if not instances or len(instances) == 1:
            return True, "Configuration graph is connected."

        parent = {instance: instance for instance in instances}
        rank = {instance: 0 for instance in instances}

        def find(node: str) -> str:
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left: str, right: str) -> None:
            root_left = find(left)
            root_right = find(right)
            if root_left == root_right:
                return
            if rank[root_left] < rank[root_right]:
                parent[root_left] = root_right
            elif rank[root_left] > rank[root_right]:
                parent[root_right] = root_left
            else:
                parent[root_right] = root_left
                rank[root_left] += 1

        for left, right in edges:
            union(left, right)

        roots = {find(instance) for instance in instances}
        if len(roots) == 1:
            return True, "Configuration graph is connected."

        components: dict[str, list[str]] = {}
        for instance in instances:
            components.setdefault(find(instance), []).append(instance)
        parts = [
            f"Component {index + 1}: [{', '.join(sorted(component))}]"
            for index, component in enumerate(components.values())
        ]
        return False, "Configuration has disconnected components:\n" + "\n".join(parts)

    def _disjoint_class_pairs(self) -> set[frozenset[URIRef]]:
        pairs: set[frozenset[URIRef]] = set()
        ontology_graph = self.ontology.graph

        for left, _, right in ontology_graph.triples((None, OWL.disjointWith, None)):
            if isinstance(left, URIRef) and isinstance(right, URIRef):
                pairs.add(frozenset((left, right)))

        for node in ontology_graph.subjects(RDF.type, OWL.AllDisjointClasses):
            members_node = ontology_graph.value(node, OWL.members)
            if members_node is None:
                continue
            try:
                members = [
                    member for member in Collection(ontology_graph, members_node)
                    if isinstance(member, URIRef)
                ]
            except Exception:
                continue
            for left, right in combinations(members, 2):
                pairs.add(frozenset((left, right)))

        return pairs

    def _functional_properties(self) -> set[URIRef]:
        return {
            prop for prop in self.ontology.graph.subjects(RDF.type, OWL.FunctionalProperty)
            if isinstance(prop, URIRef)
        }

    def _class_label(self, class_uri: URIRef) -> str:
        return self.ontology.get_class_name(class_uri) or str(class_uri)

    def _property_label(self, property_uri: URIRef) -> str:
        return self.ontology.get_property_name(property_uri) or str(property_uri)

    @staticmethod
    def _is_instance_node(node) -> bool:
        return isinstance(node, BNode) or (isinstance(node, URIRef) and str(node).startswith(INSTANCE_NS))

    @staticmethod
    def _instance_label(node: Node) -> str:
        if isinstance(node, URIRef):
            return str(node).removeprefix(INSTANCE_NS)
        return str(node)

    @staticmethod
    def _error(category: str, message: str) -> str:
        return f"[error][{category}] {message}"

    @staticmethod
    def _check_result(rule_name: str, messages: list[str]) -> CheckResult:
        return CheckResult(
            rule_name=rule_name,
            is_valid=not any(message.startswith("[error]") for message in messages),
            messages=messages,
        )
