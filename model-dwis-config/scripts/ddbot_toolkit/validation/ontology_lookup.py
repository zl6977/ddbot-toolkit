from __future__ import annotations

from pathlib import Path
from typing import Optional

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

INSTANCE_NS = "http://ddhub.no/instance/"
ONTOLOGY_NS = "http://ddhub.no/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


class DWISOntology:
    def __init__(self, ontology_path: str | Path):
        self.ontology_path = Path(ontology_path)
        self.graph = Graph()
        self.classes: dict[str, dict] = {}
        self.properties: dict[str, dict] = {}
        self._property_constraints_cache: dict[str, tuple[tuple[URIRef, ...], tuple[URIRef, ...]]] = {}
        self._subclass_cache: dict[tuple[URIRef, URIRef], bool] = {}
        self._load()

    def _get_label(self, uri: URIRef) -> str:
        uri_str = str(uri)
        if uri.fragment:
            return uri.fragment
        if "#" in uri_str and uri_str.split("#")[-1]:
            return uri_str.split("#")[-1]
        if "/" in uri_str and uri_str.split("/")[-1]:
            return uri_str.split("/")[-1]
        return uri_str

    def _load(self) -> None:
        self.graph.parse(self.ontology_path, format="turtle")
        for subj, _, obj in self.graph:
            if isinstance(subj, BNode):
                continue
            if obj in {OWL.Class, RDFS.Class}:
                class_entry = self.classes.setdefault(self._get_label(subj), {"uri": subj})
                for _, _, super_obj in self.graph.triples((subj, RDFS.subClassOf, None)):
                    if isinstance(super_obj, URIRef):
                        class_entry["superclass"] = super_obj
                        break
                for _, _, comment_obj in self.graph.triples((subj, RDFS.comment, None)):
                    class_entry["comment"] = str(comment_obj)
                    break
            elif obj in {OWL.ObjectProperty, OWL.DatatypeProperty}:
                prop_type = "object" if obj == OWL.ObjectProperty else "data"
                prop_entry = self.properties.setdefault(
                    self._get_label(subj),
                    {"uri": subj, "domain": [], "range": [], "property_type": prop_type},
                )
                for _, _, super_obj in self.graph.triples((subj, RDFS.subPropertyOf, None)):
                    if isinstance(super_obj, URIRef):
                        prop_entry["superproperty"] = super_obj
                        break
                for _, _, domain_obj in self.graph.triples((subj, RDFS.domain, None)):
                    if isinstance(domain_obj, URIRef):
                        prop_entry["domain"].append(domain_obj)
                for _, _, range_obj in self.graph.triples((subj, RDFS.range, None)):
                    if isinstance(range_obj, URIRef):
                        prop_entry["range"].append(range_obj)
                for _, _, comment_obj in self.graph.triples((subj, RDFS.comment, None)):
                    prop_entry["comment"] = str(comment_obj)
                    break

    def get_class_uri(self, class_name: str) -> Optional[URIRef]:
        return self.classes.get(class_name, {}).get("uri")

    def get_property_uri(self, property_name: str) -> Optional[URIRef]:
        return self.properties.get(property_name, {}).get("uri")

    def get_class_name(self, class_uri: URIRef) -> Optional[str]:
        for name, data in self.classes.items():
            if data.get("uri") == class_uri:
                return name
        return None

    def get_property_name(self, property_uri: URIRef) -> Optional[str]:
        for name, data in self.properties.items():
            if data.get("uri") == property_uri:
                return name
        return None

    def resolve_class_name(self, name: str) -> Optional[str]:
        if name in self.classes:
            return name
        if f"{name}Quantity" in self.classes:
            return f"{name}Quantity"
        return None

    def is_object_property(self, property_name: str) -> bool:
        return self.properties.get(property_name, {}).get("property_type") == "object"

    def is_data_property(self, property_name: str) -> bool:
        return self.properties.get(property_name, {}).get("property_type") == "data"

    def compact_uri(self, uri: URIRef | BNode | str) -> str:
        if isinstance(uri, BNode):
            return f"_:{uri}"
        uri_str = str(uri)
        # INSTANCE_NS is a subpath of ONTOLOGY_NS, so it must be tested first.
        if uri_str.startswith(INSTANCE_NS):
            return f"inst:{uri_str.removeprefix(INSTANCE_NS)}"
        if uri_str == str(RDF.type):
            return "rdf:type"
        if uri_str.startswith(ONTOLOGY_NS):
            return f"ontology:{uri_str.removeprefix(ONTOLOGY_NS)}"
        return uri_str

    def get_property_constraints(self, predicate: str) -> tuple[tuple[URIRef, ...], tuple[URIRef, ...]]:
        cached = self._property_constraints_cache.get(predicate)
        if cached is not None:
            return cached

        prop_data = self.properties.get(predicate)
        if prop_data is None:
            return tuple(), tuple()

        to_visit = [URIRef(prop_data["uri"])]
        seen = set()
        domains = set()
        ranges = set()

        while to_visit:
            current = to_visit.pop()
            if current in seen:
                continue
            seen.add(current)

            for _, _, domain in self.graph.triples((current, RDFS.domain, None)):
                if isinstance(domain, URIRef):
                    domains.add(domain)
            for _, _, range_ in self.graph.triples((current, RDFS.range, None)):
                if isinstance(range_, URIRef):
                    ranges.add(range_)
            for _, _, super_prop in self.graph.triples((current, RDFS.subPropertyOf, None)):
                if isinstance(super_prop, URIRef):
                    to_visit.append(super_prop)

        cached = (tuple(sorted(domains, key=str)), tuple(sorted(ranges, key=str)))
        self._property_constraints_cache[predicate] = cached
        return cached

    def _is_subclass_of(self, child: URIRef, parent: URIRef) -> bool:
        key = (child, parent)
        cached = self._subclass_cache.get(key)
        if cached is not None:
            return cached

        if child == parent:
            self._subclass_cache[key] = True
            return True

        stack = [child]
        seen = set()

        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for _, _, super_class in self.graph.triples((current, RDFS.subClassOf, None)):
                if not isinstance(super_class, URIRef):
                    continue
                if super_class == parent:
                    self._subclass_cache[key] = True
                    return True
                stack.append(super_class)

        self._subclass_cache[key] = False
        return False

    def is_subclass_of_uri(self, child: URIRef, parent: URIRef) -> bool:
        """Return True if *child* is equal to or a subclass of *parent* (URI form)."""
        return self._is_subclass_of(child, parent)

    def is_subclass_of(self, child_name: str, parent_name: str) -> bool:
        """Return True if *child_name* is equal to or a subclass of *parent_name*.

        Both names are resolved via the class registry; returns False if
        either name is not a known ontology class.
        """
        child_uri = self.get_class_uri(child_name)
        parent_uri = self.get_class_uri(parent_name)
        if child_uri is None or parent_uri is None:
            return False
        return self._is_subclass_of(child_uri, parent_uri)

    def node_matches_constraints(self, graph: Graph, node: URIRef, constraints: tuple[URIRef, ...]) -> bool:
        if not constraints:
            return True

        node_types = [obj for _, _, obj in graph.triples((node, RDF.type, None)) if isinstance(obj, URIRef)]
        if not node_types:
            return False

        for node_type in node_types:
            for constraint in constraints:
                if self._is_subclass_of(node_type, constraint):
                    return True
        return False
