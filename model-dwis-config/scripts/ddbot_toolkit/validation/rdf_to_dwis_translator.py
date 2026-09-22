from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD

from .ontology_lookup import INSTANCE_NS, DWISOntology


@dataclass
class _RDFToDWISModel:
    types: dict[URIRef | BNode, list[str]] = field(default_factory=dict)
    relations: list[tuple[URIRef | BNode, str, URIRef | BNode]] = field(default_factory=list)
    properties: list[tuple[URIRef | BNode, str, Literal]] = field(default_factory=list)
    bnode_ref_count: dict[BNode, int] = field(default_factory=dict)
    bnode_is_subject: set[BNode] = field(default_factory=set)


class RDFToDWISTranslator:
    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def translate(self, graph: Graph) -> str:
        model = self._collect(graph)
        return self._emit(model)

    def _collect(self, graph: Graph) -> _RDFToDWISModel:
        model = _RDFToDWISModel()

        for subj, pred, obj in graph:
            if not self._is_instance_node(subj):
                continue

            if pred == RDF.type:
                if not isinstance(obj, URIRef):
                    continue
                class_name = self.ontology.get_class_name(obj)
                if class_name is not None:
                    model.types.setdefault(subj, []).append(class_name)
                continue

            pred_name = self.ontology.get_property_name(pred)
            if pred_name is None:
                continue
            if isinstance(obj, Literal):
                model.properties.append((subj, pred_name, obj))
                continue
            if not self._is_instance_node(obj):
                continue
            model.relations.append((subj, pred_name, obj))
            if isinstance(obj, BNode):
                model.bnode_ref_count[obj] = model.bnode_ref_count.get(obj, 0) + 1
            if isinstance(subj, BNode):
                model.bnode_is_subject.add(subj)

        return model

    def _emit(self, model: _RDFToDWISModel) -> str:
        bnode_ids = self._mint_bnode_ids(model)

        def node_id(node: URIRef | BNode) -> str | None:
            if isinstance(node, URIRef):
                return self._instance_id(node)
            return bnode_ids.get(node)

        declaration_lines: list[str] = []
        declaration_nodes: list[tuple[str, str, list[str], URIRef | BNode]] = []
        for node, class_names in model.types.items():
            if isinstance(node, BNode) and self._is_shorthand_bnode(node, model):
                continue
            identifier = node_id(node)
            if identifier is None or " " in identifier or ":" in identifier:
                continue
            primary, rest = self._most_specific(class_names)
            declaration_nodes.append((primary, identifier, rest, node))

        declaration_nodes.sort(key=lambda item: (item[0], item[1]))
        for primary, identifier, rest, _ in declaration_nodes:
            declaration_lines.append(f"{primary}:{identifier}")
            for class_name in rest:
                declaration_lines.append(f"{class_name}:{identifier}")

        relation_lines: list[tuple[str, str, str]] = []
        for subj, pred_name, obj in model.relations:
            subject_id = node_id(subj)
            if subject_id is None:
                continue

            if isinstance(obj, BNode) and self._is_shorthand_bnode(obj, model):
                class_names = model.types.get(obj, [])
                if class_names:
                    primary, _ = self._most_specific(class_names)
                    relation_lines.append((subject_id, pred_name, primary))
                    continue

            object_id = node_id(obj)
            if object_id is None:
                continue
            relation_lines.append((subject_id, pred_name, object_id))

        relation_lines.sort(key=lambda item: (item[0], item[1], item[2]))
        relation_strings = [f"{subj} {pred} {obj}" for subj, pred, obj in relation_lines]

        property_lines: list[str] = []
        for subj, prop_name, literal in sorted(model.properties, key=lambda item: (str(item[0]), item[1])):
            instance_id = node_id(subj)
            if instance_id is None:
                continue
            property_lines.append(f"{instance_id}.{prop_name} = {self._format_literal(literal)}")

        parts = []
        if declaration_lines:
            parts.append("\n".join(declaration_lines))
        if relation_strings:
            parts.append("\n".join(relation_strings))
        if property_lines:
            parts.append("\n".join(property_lines))
        return "\n\n".join(parts)

    @staticmethod
    def _format_literal(literal: Literal) -> str:
        """Render an rdflib Literal back into DWIS literal syntax."""
        if literal.datatype == XSD.boolean:
            return "true" if literal.value else "false"
        if literal.datatype in {XSD.integer, XSD.int, XSD.double, XSD.decimal, XSD.float}:
            return str(literal.value)
        return f'"{literal.value}"'

    def _most_specific(self, class_names: list[str]) -> tuple[str, list[str]]:
        if len(class_names) == 1:
            return class_names[0], []

        leaves: list[str] = []
        for candidate in class_names:
            is_ancestor = any(
                other != candidate and self.ontology.is_subclass_of(other, candidate)
                for other in class_names
            )
            if not is_ancestor:
                leaves.append(candidate)

        if not leaves:
            leaves = list(class_names)

        leaves.sort()
        primary = leaves[0]
        rest = sorted(class_name for class_name in class_names if class_name != primary)
        return primary, rest

    def _is_shorthand_bnode(self, bnode: BNode, model: _RDFToDWISModel) -> bool:
        if model.bnode_ref_count.get(bnode, 0) != 1:
            return False
        if bnode in model.bnode_is_subject:
            return False
        class_names = model.types.get(bnode, [])
        if len(class_names) != 1:
            return False
        _, rest = self._most_specific(class_names)
        return not rest

    def _mint_bnode_ids(self, model: _RDFToDWISModel) -> dict[BNode, str]:
        promoted: list[tuple[BNode, str, tuple[str, ...]]] = []

        for node, class_names in model.types.items():
            if not isinstance(node, BNode) or self._is_shorthand_bnode(node, model):
                continue
            primary, rest = self._most_specific(class_names)
            rel_sig = []
            for subj, pred_name, obj in model.relations:
                if subj is node:
                    rel_sig.append(("s", pred_name, self._node_sort_key(obj, model)))
                if obj is node:
                    rel_sig.append(("o", pred_name, self._node_sort_key(subj, model)))
            rel_sig.sort()
            promoted.append((node, primary, (primary, tuple(rest), tuple(str(item) for item in rel_sig))))

        promoted.sort(key=lambda item: item[2])
        return {bnode: f"{primary}_bnode_{index}" for index, (bnode, primary, _) in enumerate(promoted)}

    @staticmethod
    def _node_sort_key(node: URIRef | BNode, model: _RDFToDWISModel) -> str:
        if isinstance(node, URIRef):
            return str(node)
        return ",".join(sorted(model.types.get(node, [])))

    @staticmethod
    def _instance_id(node: URIRef | BNode) -> str | None:
        if isinstance(node, URIRef):
            uri_str = str(node)
            if uri_str.startswith(INSTANCE_NS):
                return uri_str[len(INSTANCE_NS):]
        return None

    @staticmethod
    def _is_instance_node(node) -> bool:
        return isinstance(node, BNode) or (isinstance(node, URIRef) and str(node).startswith(INSTANCE_NS))
