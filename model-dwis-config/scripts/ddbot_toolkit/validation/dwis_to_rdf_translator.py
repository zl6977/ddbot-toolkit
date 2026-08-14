from __future__ import annotations

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF
from rdflib.term import Node

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

        return graph

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


def serialize_rdf_turtle(graph: Graph) -> str:
    turtle_graph = Graph()
    turtle_graph.bind("inst", INSTANCE_NS)
    turtle_graph.bind("ddhub", "http://ddhub.no/")
    turtle_graph.bind("rdf", RDF)
    turtle_graph.bind("owl", OWL)
    for triple in graph:
        turtle_graph.add(triple)
    return turtle_graph.serialize(format="turtle").strip()
