"""
The HealthDCAT-AP Release 8 profile, on the dataset-level properties.

Pure tests: no CKAN database, no scheming plugin. The dataset schema is a small one
defined here and handed to the profile through ``base.get_action``, like the other
health profile tests do.
"""
import logging
from unittest import mock

import pytest
from rdflib import RDF, XSD, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS as DCT
from rdflib.namespace import Namespace

from ckanext.dcat.profiles import (
    EuropeanHealthDCATAPProfile,
    EuropeanHealthDCATAPR8Profile,
    base,
)

DCAT = Namespace("http://www.w3.org/ns/dcat#")
DPV = Namespace("https://w3id.org/dpv#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
OA = Namespace("http://www.w3.org/ns/oa#")
HEALTHDCATAP = Namespace("http://healthdataportal.eu/ns/health#")

DATASET = URIRef("http://example.org/dataset")


def _field(name, **extra):
    return {"field_name": name, "label": name, **extra}


SCHEMA = {
    "scheming_version": 2,
    "dataset_type": "dataset",
    "form_languages": ["en", "nl"],
    "dataset_fields": [
        _field("identifier"),
        _field("alternative_title", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("has_structured_data", preset="select", validators="ignore_missing boolean_validator"),
        _field("related_resource", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("source", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("code_values", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("coding_system", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("legal_basis", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("personal_data", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        _field("purpose", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
    ],
    "resource_fields": [],
}


def _profile(graph, profile_class=EuropeanHealthDCATAPR8Profile):
    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: SCHEMA):
        return profile_class(graph)


def parse(turtle, profile_class=EuropeanHealthDCATAPR8Profile):
    graph = Graph().parse(data=turtle, format="turtle")
    return _profile(graph, profile_class).parse_dataset({"extras": []}, DATASET)


def serialize(dataset_dict, profile_class=EuropeanHealthDCATAPR8Profile):
    graph = Graph()
    _profile(graph, profile_class).graph_from_dataset({"id": "1", "name": "test", **dataset_dict}, DATASET)
    return graph


def values(graph, predicate, subject=DATASET):
    return sorted(graph.objects(subject, predicate), key=str)


PREFIXES = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dpv: <https://w3id.org/dpv#> .
@prefix healthdcatap: <http://healthdataportal.eu/ns/health#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


class TestAlternativeTitle:
    def test_every_dct_alternative_is_parsed(self):
        dataset = parse(
            PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; dct:alternative "EU cohort"@en , "EU cohorte"@nl .'
        )

        assert sorted(dataset["alternative_title"]) == ["EU cohort", "EU cohorte"]

    def test_no_alternative_gives_no_field(self):
        assert "alternative_title" not in parse(PREFIXES + "<http://example.org/dataset> a dcat:Dataset .")

    def test_every_alternative_title_is_serialized_as_a_literal(self):
        graph = serialize({"alternative_title": ["EU cohort", "Other"]})

        assert values(graph, DCT.alternative) == [Literal("EU cohort"), Literal("Other")]

    def test_the_value_may_be_a_json_list(self):
        graph = serialize({"alternative_title": '["EU cohort"]'})

        assert values(graph, DCT.alternative) == [Literal("EU cohort")]


class TestHasStructuredData:
    @pytest.mark.parametrize("lexical, expected", [("true", True), ("false", False), ("1", True), ("0", False)])
    def test_the_boolean_is_parsed(self, lexical, expected):
        dataset = parse(
            PREFIXES
            + f'<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hasStructuredData "{lexical}"^^xsd:boolean .'
        )

        assert dataset["has_structured_data"] is expected

    def test_a_value_that_is_not_a_boolean_is_ignored(self):
        dataset = parse(
            PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hasStructuredData "maybe" .'
        )

        assert "has_structured_data" not in dataset

    @pytest.mark.parametrize("value, expected", [(True, True), (False, False), ("true", True), ("False", False)])
    def test_the_boolean_is_serialized_with_its_datatype(self, value, expected):
        graph = serialize({"has_structured_data": value})

        assert values(graph, HEALTHDCATAP.hasStructuredData) == [Literal(expected, datatype=XSD.boolean)]

    @pytest.mark.parametrize("value", [None, ""])
    def test_an_empty_value_is_not_serialized(self, value):
        assert values(serialize({"has_structured_data": value}), HEALTHDCATAP.hasStructuredData) == []


class TestTypedObjects:
    """R8 checks the class of the IRIs behind these properties."""

    @pytest.mark.parametrize(
        "key, predicate, rdf_class",
        [
            ("coding_system", HEALTHDCATAP.hasCodingSystem, DCT.Standard),
            ("legal_basis", DPV.hasLegalBasis, DPV.LegalBasis),
            ("personal_data", DPV.hasPersonalData, DPV.PersonalData),
            ("purpose", DPV.hasPurpose, DPV.Purpose),
        ],
    )
    def test_the_iri_gets_the_range_class(self, key, predicate, rdf_class):
        iri = "http://example.org/thing"

        graph = serialize({key: [iri]})

        assert (URIRef(iri), RDF.type, rdf_class) in graph
        assert values(graph, predicate) == [URIRef(iri)]

    def test_a_literal_is_left_without_a_type(self):
        graph = serialize({"legal_basis": ["consent"]})

        assert values(graph, DPV.hasLegalBasis) == [Literal("consent")]
        assert not list(graph.subjects(RDF.type, DPV.LegalBasis))

    def test_the_health_dcat_ap_profile_does_not_write_the_types(self):
        graph = serialize({"legal_basis": ["http://example.org/thing"]}, EuropeanHealthDCATAPProfile)

        assert not list(graph.subjects(RDF.type, DPV.LegalBasis))


class TestCodeValues:
    def test_an_iri_is_written_as_a_literal(self):
        graph = serialize({"code_values": ["http://example.org/code/U07.1", "U07.2"]})

        assert values(graph, HEALTHDCATAP.hasCodeValues) == [
            Literal("U07.2"),
            Literal("http://example.org/code/U07.1"),
        ]

    def test_the_health_dcat_ap_profile_still_writes_an_iri(self):
        graph = serialize({"code_values": ["http://example.org/code/U07.1"]}, EuropeanHealthDCATAPProfile)

        assert values(graph, HEALTHDCATAP.hasCodeValues) == [URIRef("http://example.org/code/U07.1")]


class TestQualityAnnotation:
    ANNOTATION = {
        "quality_annotation": [
            {
                "body": "https://quality.example.org/certificates/1",
                "target": "http://example.org/dataset",
                "motivated_by": "http://www.w3.org/ns/dqv#qualityAssessment",
            }
        ]
    }

    def test_it_is_a_quality_certificate(self):
        graph = serialize(self.ANNOTATION)

        (annotation,) = values(graph, DQV.hasQualityAnnotation)
        assert list(graph.objects(annotation, RDF.type)) == [DQV.QualityCertificate]
        assert values(graph, OA.hasBody, annotation) == [URIRef("https://quality.example.org/certificates/1")]

    def test_the_health_dcat_ap_profile_still_writes_an_annotation(self):
        graph = serialize(self.ANNOTATION, EuropeanHealthDCATAPProfile)

        (annotation,) = values(graph, DQV.hasQualityAnnotation)
        assert list(graph.objects(annotation, RDF.type)) == [OA.Annotation]


class TestNotAnR8Property:
    TRUSTED = PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; healthdcatap:trustedDataHolder "true"^^xsd:boolean .'

    def test_trusted_data_holder_is_not_parsed(self):
        assert "trusted_data_holder" not in parse(self.TRUSTED)

    def test_the_health_dcat_ap_profile_parses_it(self):
        assert parse(self.TRUSTED, EuropeanHealthDCATAPProfile)["trusted_data_holder"] is True


class TestSingleValuedFields:
    """Q3: the field keeps one value and a warning says when others are dropped (ADR 0001)."""

    def test_several_identifiers_give_a_warning_and_one_value(self, caplog):
        with caplog.at_level(logging.WARNING):
            dataset = parse(PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; dct:identifier "a", "b" .')

        assert dataset["identifier"] in ("a", "b")
        assert any("identifier" in r.getMessage() and "only the first is kept" in r.getMessage() for r in caplog.records)

    def test_several_types_give_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            parse(
                PREFIXES
                + "<http://example.org/dataset> a dcat:Dataset ; dct:type <http://example.org/t1>, <http://example.org/t2> ."
            )

        assert any("dcat_type" in r.getMessage() for r in caplog.records)

    def test_several_landing_pages_give_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            parse(
                PREFIXES
                + "<http://example.org/dataset> a dcat:Dataset ; dcat:landingPage <http://example.org/p1>, <http://example.org/p2> ."
            )

        assert any("landingPage" in r.getMessage() for r in caplog.records)

    def test_one_value_gives_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            parse(PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; dct:identifier "a" ; dct:type <http://example.org/t1> .')

        assert not caplog.records
