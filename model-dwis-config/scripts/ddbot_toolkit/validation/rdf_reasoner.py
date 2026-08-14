from __future__ import annotations

import owlrl
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from .ontology_lookup import INSTANCE_NS, DWISOntology
from .schemas import ReasoningResult

SIZE_WARNING_RATIO = 3.0
SIZE_WARNING_FLOOR = 10

_CLASS_FOLLOW = (RDFS.subClassOf, OWL.equivalentClass)
_PROPERTY_FOLLOW = (RDFS.subPropertyOf, OWL.inverseOf, OWL.equivalentProperty)


class RDFReasoner:
    def __init__(
        self,
        ontology: DWISOntology,
        *,
        size_warning_ratio: float = SIZE_WARNING_RATIO,
        size_warning_floor: int = SIZE_WARNING_FLOOR,
        use_full_ontology: bool = False,
        prune_to_most_specific: bool = False,
    ):
        self.ontology = ontology
        self.size_warning_ratio = size_warning_ratio
        self.size_warning_floor = size_warning_floor
        self.use_full_ontology = use_full_ontology
        self.prune_to_most_specific = prune_to_most_specific
        self._closed_tbox = self._closure(self._copy(ontology.graph)) if use_full_ontology else None

    def reason(self, asserted_graph: Graph) -> tuple[Graph, ReasoningResult]:
        warnings: list[str] = []
        if len(asserted_graph) == 0:
            return Graph(), ReasoningResult(warnings=warnings)

        raw_count = sum(1 for triple in asserted_graph if self._keep(*triple))
        working = self._build_working_graph(asserted_graph)
        self._closure(working)

        inferred_graph = Graph()
        for triple in working:
            if self._keep(*triple):
                inferred_graph.add(triple)

        if self.prune_to_most_specific:
            self._prune_types(inferred_graph)

        inferred_count = len(inferred_graph)
        ratio = inferred_count / raw_count if raw_count else float(inferred_count or 1)
        size_warning = (
            raw_count > 0
            and ratio >= self.size_warning_ratio
            and (inferred_count - raw_count) >= self.size_warning_floor
        )
        if size_warning:
            warnings.append(
                f"[warning][structural] Inferred graph is {ratio:.1f}x larger than the asserted graph "
                f"({inferred_count} vs {raw_count} triples); this may indicate an unexpected predicate, "
                f"broad domain/range, or broad property hierarchy."
            )

        return inferred_graph, ReasoningResult(
            warnings=warnings,
            inferred_size_ratio=round(ratio, 3),
            inferred_size_warning=size_warning,
        )

    def _build_working_graph(self, asserted_graph: Graph) -> Graph:
        if self.use_full_ontology:
            working = self._copy(self._closed_tbox)
        else:
            working = self._tbox_subset(asserted_graph)
        for triple in asserted_graph:
            working.add(triple)
        return working

    def _tbox_subset(self, instance_graph: Graph) -> Graph:
        ontology_graph = self.ontology.graph
        subset = Graph()

        property_seeds: set[URIRef] = set()
        class_seeds: set[URIRef] = set()
        for _, pred, obj in instance_graph:
            if pred == RDF.type and isinstance(obj, URIRef):
                class_seeds.add(obj)
            elif isinstance(pred, URIRef):
                property_seeds.add(pred)

        seen_props: set[URIRef] = set()
        prop_stack = list(property_seeds)
        while prop_stack:
            prop = prop_stack.pop()
            if prop in seen_props:
                continue
            seen_props.add(prop)
            for subj, pred, obj in ontology_graph.triples((prop, None, None)):
                subset.add((subj, pred, obj))
                if isinstance(obj, URIRef):
                    if pred in (RDFS.domain, RDFS.range):
                        class_seeds.add(obj)
                    elif pred in _PROPERTY_FOLLOW:
                        prop_stack.append(obj)

        seen_classes: set[URIRef] = set()
        class_stack = list(class_seeds)
        while class_stack:
            cls = class_stack.pop()
            if cls in seen_classes:
                continue
            seen_classes.add(cls)
            for subj, pred, obj in ontology_graph.triples((cls, None, None)):
                subset.add((subj, pred, obj))
                if pred in _CLASS_FOLLOW and isinstance(obj, URIRef):
                    class_stack.append(obj)

        return subset

    def _keep(self, subj, pred, obj) -> bool:
        if not self._is_instance_node(subj):
            return False
        if pred == RDF.type:
            return isinstance(obj, URIRef) and self.ontology.get_class_name(obj) is not None
        if not isinstance(pred, URIRef) or self.ontology.get_property_name(pred) is None:
            return False
        if isinstance(obj, Literal):
            return False
        return self._is_instance_node(obj)

    def _prune_types(self, graph: Graph) -> None:
        types_by_subject: dict[URIRef | BNode, list[URIRef]] = {}
        for subj, pred, obj in graph:
            if pred == RDF.type and isinstance(obj, URIRef):
                types_by_subject.setdefault(subj, []).append(obj)

        for subj, type_uris in types_by_subject.items():
            if len(type_uris) < 2:
                continue
            for candidate in type_uris:
                for other in type_uris:
                    if other == candidate:
                        continue
                    if self.ontology.is_subclass_of_uri(other, candidate) and not self.ontology.is_subclass_of_uri(
                        candidate, other
                    ):
                        graph.remove((subj, RDF.type, candidate))
                        break

    @staticmethod
    def _is_instance_node(node) -> bool:
        return isinstance(node, BNode) or (isinstance(node, URIRef) and str(node).startswith(INSTANCE_NS))

    @staticmethod
    def _copy(graph: Graph | None) -> Graph:
        clone = Graph()
        if graph is None:
            return clone
        for triple in graph:
            clone.add(triple)
        return clone

    @staticmethod
    def _closure(graph: Graph) -> Graph:
        owlrl.DeductiveClosure(
            owlrl.RDFS_OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(graph)
        return graph
