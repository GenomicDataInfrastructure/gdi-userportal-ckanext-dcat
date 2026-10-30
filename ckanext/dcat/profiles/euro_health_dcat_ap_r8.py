import logging

from rdflib import DCAT, RDF, XSD, Literal, URIRef
from rdflib.namespace import DCTERMS as DCT

from ckanext.dcat.profiles.euro_health_dcat_ap import (
    DPV,
    DQV,
    HEALTHDCATAP,
    OA,
    EuropeanHealthDCATAPProfile,
)

log = logging.getLogger(__name__)

# R8 types the IRIs behind these properties; the data they point to usually carries no type
# of its own, and the shapes check the class (HealthDCAT-AP R8, ranges/range.ttl).
TYPED_OBJECTS = (
    (HEALTHDCATAP.hasCodingSystem, DCT.Standard),
    (DPV.hasLegalBasis, DPV.LegalBasis),
    (DPV.hasPersonalData, DPV.PersonalData),
    (DPV.hasPurpose, DPV.Purpose),
)

# R8 allows several values where the CKAN field holds one. The field stays single-valued
# (ADR 0001, Q3): the first value is kept and the others are dropped, with a warning.
SINGLE_VALUED = (
    (DCT.identifier, "identifier"),
    (DCT.type, "dcat_type"),
    (DCAT.landingPage, "url"),
)

BOOLEANS = {"true": True, "1": True, "false": False, "0": False}


class EuropeanHealthDCATAPR8Profile(EuropeanHealthDCATAPProfile):
    """
    A profile implementing HealthDCAT-AP Release 8.

    It builds on the HealthDCAT-AP profile and overrides only where R8 differs, so the
    fields and mapping R8 shares with it stay in one place. The CKAN field names are
    the profile-neutral ones; only the RDF mapping depends on the version.

    https://data.health.europa.eu/healthdcat-ap/releases/release-8/
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        dataset_dict = super().parse_dataset(dataset_dict, dataset_ref)

        # Not an R8 property, and the R8 schema has no field for it
        dataset_dict.pop("trusted_data_holder", None)

        alternative_titles = self._object_value_list(dataset_ref, DCT.alternative)
        if alternative_titles:
            dataset_dict["alternative_title"] = alternative_titles

        structured_data = self._object_value(dataset_ref, HEALTHDCATAP.hasStructuredData)
        if structured_data is not None and structured_data.lower() in BOOLEANS:
            dataset_dict["has_structured_data"] = BOOLEANS[structured_data.lower()]

        for predicate, field in SINGLE_VALUED:
            self._warn_about_dropped_values(dataset_ref, predicate, field)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        super().graph_from_dataset(dataset_dict, dataset_ref)

        self.g.bind("dqv", DQV)
        self.g.bind("oa", OA)

        self._add_list_triples_from_dict(
            dataset_dict,
            dataset_ref,
            [("alternative_title", DCT.alternative, None, Literal)],
        )

        structured_data = self._get_dict_value(dataset_dict, "has_structured_data")
        if structured_data not in (None, ""):
            self.g.add(
                (
                    dataset_ref,
                    HEALTHDCATAP.hasStructuredData,
                    Literal(str(structured_data).lower() in ("true", "1"), datatype=XSD.boolean),
                )
            )

        self._type_the_objects(dataset_ref)
        self._write_code_values_as_literals(dataset_ref)
        self._write_quality_annotations_as_certificates(dataset_ref)

    def _warn_about_dropped_values(self, subject_ref, predicate, field):
        values = {str(value) for value in self.g.objects(subject_ref, predicate)}
        if len(values) > 1:
            log.warning(
                "%s has %d values for %s but the field %s holds one; only the first is kept",
                subject_ref,
                len(values),
                predicate,
                field,
            )

    def _type_the_objects(self, dataset_ref):
        for predicate, rdf_class in TYPED_OBJECTS:
            for value in self.g.objects(dataset_ref, predicate):
                if isinstance(value, URIRef):
                    self.g.add((value, RDF.type, rdf_class))

    def _write_code_values_as_literals(self, dataset_ref):
        """R8 gives hasCodeValues a literal range; the HealthDCAT-AP profile writes an IRI for http(s) values."""
        for value in list(self.g.objects(dataset_ref, HEALTHDCATAP.hasCodeValues)):
            if isinstance(value, URIRef):
                self.g.remove((dataset_ref, HEALTHDCATAP.hasCodeValues, value))
                self.g.add((dataset_ref, HEALTHDCATAP.hasCodeValues, Literal(str(value))))

    def _write_quality_annotations_as_certificates(self, dataset_ref):
        """R8's range for dqv:hasQualityAnnotation is dqv:QualityCertificate, not oa:Annotation."""
        for annotation_ref in self.g.objects(dataset_ref, DQV.hasQualityAnnotation):
            self.g.remove((annotation_ref, RDF.type, OA.Annotation))
            self.g.add((annotation_ref, RDF.type, DQV.QualityCertificate))
