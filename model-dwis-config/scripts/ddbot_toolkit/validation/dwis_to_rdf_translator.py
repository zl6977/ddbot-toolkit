from __future__ import annotations

import json
from collections.abc import Iterable

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, XSD
from rdflib.term import Node

from .dwis_config_checker import (
    normalize_attribute_literal,
    select_compatible_attribute_datatype,
)
from .ontology_lookup import INSTANCE_NS, DWISOntology
from .schemas import CheckResult, DWISConfigLine, DWISToRDFResult


class DWISToRDFTranslator:
    def __init__(self, ontology: DWISOntology):
        self.ontology = ontology

    def translate(
        self,
        config_lines: list[DWISConfigLine],
        *,
        check_results: list[CheckResult] | None = None,
    ) -> DWISToRDFResult:
        graph = self._construct_graph(config_lines)
        return DWISToRDFResult(
            graph=graph,
            turtle=serialize_rdf_turtle(graph),
            construction_valid=True,
            messages=[],
            check_results=check_results or [],
        )


    def _construct_graph(self, config_lines: list[DWISConfigLine]) -> Graph:
        graph = Graph()
        declared_instances: set[URIRef] = set()
        blank_nodes: dict[str, BNode] = {}

        for config_line in config_lines:
            if config_line.line_type == "type":
                class_name, instance_id = DWISConfigLine.split_type(config_line.text)
                class_uri = self.ontology.get_class_uri(class_name)
                instance_uri = URIRef(f"{INSTANCE_NS}{instance_id}")
                declared_instances.add(instance_uri)
                graph.add((instance_uri, RDF.type, class_uri))

        for config_line in config_lines:
            if config_line.line_type == "relation":
                self._construct_relation(config_line.text, graph, declared_instances, blank_nodes)
            elif config_line.line_type == "property":
                self._construct_property(config_line.text, graph)

        return graph

    def _construct_property(self, line: str, graph: Graph) -> None:
        """Add 'instance.property = literal' as an RDF datatype triple."""
        instance_id, property_name, literal_text = DWISConfigLine.split_property(line)
        instance_uri = URIRef(f"{INSTANCE_NS}{instance_id}")
        property_uri = self.ontology.get_property_uri(property_name)
        ranges = self.ontology.get_property_constraints(property_name)[1]
        literal = construct_attribute_literal(literal_text, ranges)
        graph.add((instance_uri, property_uri, literal))

    def _construct_relation(
        self,
        line: str,
        graph: Graph,
        declared_instances: set[URIRef],
        blank_nodes: dict[str, BNode],
    ) -> None:
        subject_id, predicate_name, object_id = DWISConfigLine.split_relation(line)
        predicate_uri = self.ontology.get_property_uri(predicate_name)
        subject_node = URIRef(f"{INSTANCE_NS}{subject_id}")
        object_node = self._construct_relation_object(object_id, graph, declared_instances, blank_nodes)

        graph.add((subject_node, predicate_uri, object_node))

    def _construct_relation_object(
        self,
        object_id: str,
        graph: Graph,
        declared_instances: set[URIRef],
        blank_nodes: dict[str, BNode],
    ) -> Node:
        instance_uri = URIRef(f"{INSTANCE_NS}{object_id}")
        if instance_uri in declared_instances:
            return instance_uri

        class_name = self.ontology.resolve_class_name(object_id)
        class_uri = self.ontology.get_class_uri(class_name)
        if object_id not in blank_nodes:
            blank_nodes[object_id] = BNode(object_id)
        blank_node = blank_nodes[object_id]
        graph.add((blank_node, RDF.type, class_uri))
        return blank_node


def construct_attribute_literal(text: str, ranges: Iterable[URIRef]) -> Literal:
    """Construct a range-typed literal, falling back to a generic literal."""
    datatype = select_compatible_attribute_datatype(text, ranges)
    if datatype is None:
        return _parse_generic_literal(text)
    normalized = normalize_attribute_literal(text, datatype)
    if normalized is None:
        raise ValueError(f"Literal '{text}' is incompatible with datatype '{datatype}'.")
    if datatype in {XSD.string, XSD.dateTime}:
        return Literal(json.loads(normalized), datatype=datatype)
    if datatype == XSD.boolean:
        return Literal(normalized == "true", datatype=datatype)
    return Literal(normalized, datatype=datatype, normalize=False)


def _parse_generic_literal(text: str) -> Literal:
    """Preserve a value as an untyped literal when no target datatype is known."""
    if text.startswith('"') and text.endswith('"'):
        try:
            value = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
        else:
            if isinstance(value, str):
                return Literal(value)
    return Literal(text)


def serialize_rdf_turtle(graph: Graph) -> str:
    turtle_graph = Graph()
    turtle_graph.bind("inst", INSTANCE_NS)
    turtle_graph.bind("ddhub", "http://ddhub.no/")
    turtle_graph.bind("rdf", RDF)
    turtle_graph.bind("owl", OWL)
    for triple in graph:
        turtle_graph.add(triple)
    return turtle_graph.serialize(format="turtle").strip()


def parse_rdf_turtle(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return graph
