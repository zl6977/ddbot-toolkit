from __future__ import annotations

from dataclasses import dataclass

from .dwis_config_checker import DWISConfigChecker
from .dwis_to_rdf_translator import DWISToRDFTranslator
from .ontology_lookup import DWISOntology
from .rdf_diagnostic_checker import RDFDiagnosticChecker
from .rdf_reasoner import RDFReasoner


@dataclass
class ValidationComponents:
    dwis_config_checker: DWISConfigChecker
    dwis_to_rdf_translator: DWISToRDFTranslator
    rdf_reasoner: RDFReasoner
    rdf_diagnostic_checker: RDFDiagnosticChecker


def build_validation_components(
    ontology: DWISOntology,
    *,
    prune_to_most_specific: bool = False,
) -> ValidationComponents:
    return ValidationComponents(
        dwis_config_checker=DWISConfigChecker(ontology),
        dwis_to_rdf_translator=DWISToRDFTranslator(ontology),
        rdf_reasoner=RDFReasoner(ontology, prune_to_most_specific=prune_to_most_specific),
        rdf_diagnostic_checker=RDFDiagnosticChecker(ontology),
    )
