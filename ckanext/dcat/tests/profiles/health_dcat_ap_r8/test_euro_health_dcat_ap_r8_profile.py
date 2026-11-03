"""
The HealthDCAT-AP Release 8 profile, on the dataset-level properties.

Pure tests: no CKAN database, no scheming plugin. The dataset schema is a small one
defined here and handed to the profile through ``base.get_action``, like the other
health profile tests do.
"""
import json
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
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DPV = Namespace("https://w3id.org/dpv#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
OA = Namespace("http://www.w3.org/ns/oa#")
HEALTHDCATAP = Namespace("http://healthdataportal.eu/ns/health#")

CV = Namespace("http://data.europa.eu/m8g/")
TIME = Namespace("http://www.w3.org/2006/time#")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
GEODCATAP = Namespace("http://data.europa.eu/930/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
PROV = Namespace("http://www.w3.org/ns/prov#")

DATASET = URIRef("http://example.org/dataset")


def _field(name, **extra):
    return {"field_name": name, "label": name, **extra}


LISTED = {"preset": "multiple_text", "validators": "ignore_missing scheming_multiple_text"}


def _agent_subfields(*extra):
    """The agent of the R8 pack: the email, contact page and telephone of its contact point are lists."""
    return [
        _field(n, **(LISTED if n in ("email", "url", "telephone") else {}))
        for n in ("uri", "name", "name_translated", "email", "url", "type", "publisher_note", *extra)
    ]


CONTACT_POINT = ("telephone", "opening_hours", "special_opening_hours")


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
        _field("contact", repeating_subfields=[_field("uri"), _field("name"), _field("email"), _field("url")]),
        _field("publisher", repeating_subfields=_agent_subfields(*CONTACT_POINT)),
        _field("hdab", repeating_subfields=_agent_subfields(*CONTACT_POINT)),
        _field("custodian", repeating_subfields=_agent_subfields(*CONTACT_POINT)),
        _field("hdab_coordinator", repeating_subfields=_agent_subfields(*CONTACT_POINT)),
        _field("variables", repeating_subfields=[_field("title_translated"), _field("tables")]),
        _field("qualified_relation", repeating_subfields=[_field("uri"), _field("relation", **LISTED), _field("role", **LISTED)]),
        _field("qualified_attribution", repeating_subfields=[_field("agent"), _field("role", **LISTED)]),
        _field("provenance"),
    ],
    "resource_fields": [
        _field("access_services", repeating_subfields=[_field("title"), _field("documentation")]),
    ],
}


def _profile(graph, profile_class=EuropeanHealthDCATAPR8Profile, schema=SCHEMA):
    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        return profile_class(graph)


def parse(turtle, profile_class=EuropeanHealthDCATAPR8Profile, schema=SCHEMA):
    graph = Graph().parse(data=turtle, format="turtle")
    return _profile(graph, profile_class, schema).parse_dataset({"extras": []}, DATASET)


def serialize(dataset_dict, profile_class=EuropeanHealthDCATAPR8Profile, schema=SCHEMA):
    graph = Graph()
    _profile(graph, profile_class, schema).graph_from_dataset({"id": "1", "name": "test", **dataset_dict}, DATASET)
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

    @pytest.mark.parametrize("key", ["health_category", "health_theme"])
    def test_a_vocabulary_concept_iri_is_not_typed(self, key):
        """The EU vocabularies supply the class and the preferred label a typed concept needs."""
        iri = "https://hdeu-dcat.data.health.europa.eu/resource/authority/healthcategories/EHRS"

        graph = serialize({key: [iri]})

        assert not list(graph.objects(URIRef(iri), RDF.type))

    @pytest.mark.parametrize(
        "key, predicate, rdf_class, text_predicate",
        [
            ("coding_system", HEALTHDCATAP.hasCodingSystem, DCT.Standard, DCT.title),
            ("health_category", HEALTHDCATAP.healthCategory, SKOS.Concept, SKOS.prefLabel),
            ("legal_basis", DPV.hasLegalBasis, DPV.LegalBasis, DCT.description),
            ("purpose", DPV.hasPurpose, DPV.Purpose, DCT.description),
        ],
    )
    def test_free_text_becomes_a_typed_node_holding_the_text(self, key, predicate, rdf_class, text_predicate):
        graph = serialize({key: ["Consent under the EHDS"]})

        (node,) = values(graph, predicate)
        assert (node, RDF.type, rdf_class) in graph
        assert values(graph, text_predicate, node) == [Literal("Consent under the EHDS")]

    def test_the_text_of_the_typed_node_is_read_back(self):
        graph = serialize({"legal_basis": ["Consent under the EHDS"]})

        assert _profile(graph).parse_dataset({"extras": []}, DATASET)["legal_basis"] == ["Consent under the EHDS"]

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


AGENT_PREFIXES = PREFIXES + """
@prefix cv: <http://data.europa.eu/m8g/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix geodcatap: <http://data.europa.eu/930/> .
@prefix time: <http://www.w3.org/2006/time#> .
"""

HDAB_TTL = AGENT_PREFIXES + """
<http://example.org/dataset> a dcat:Dataset ;
    healthdcatap:hdab <http://example.org/hdab> ;
    healthdcatap:hdabCoordinator <http://example.org/coordinator> ;
    geodcatap:custodian <http://example.org/custodian> .

<http://example.org/hdab> a foaf:Agent ;
    foaf:name "Belgian HDAB"@en ;
    cv:contactPoint [
        a cv:ContactPoint ;
        cv:email "hdab@example.org" ;
        cv:contactPage <https://example.org/contact> ;
        cv:telephone "+32 2 555 0102" ;
        cv:openingHours [ a time:TemporalEntity ; dct:description "Weekdays 08:30-16:30"@en ;
                          cv:frequency <http://publications.europa.eu/resource/authority/frequency/DAILY> ] ;
        cv:specialOpeningHoursSpecification [ a time:TemporalEntity ; dct:description "Closed on holidays"@en ]
    ] .

<http://example.org/coordinator> a foaf:Agent ; foaf:name "Coordinator" ;
    cv:contactPoint [ a cv:ContactPoint ; cv:email "coordinator@example.org" ] .
<http://example.org/custodian> a foaf:Agent ; foaf:name "Custodian" ;
    cv:contactPoint [ a cv:ContactPoint ; cv:contactPage <https://example.org/custodian> ] .
"""


class TestHealthAgents:
    def test_the_contact_point_is_read_into_the_flat_subfields(self):
        (hdab,) = parse(HDAB_TTL)["hdab"]

        assert hdab["email"] == ["hdab@example.org"]
        assert hdab["url"] == ["https://example.org/contact"]
        assert hdab["telephone"] == ["+32 2 555 0102"]
        assert hdab["opening_hours"] == [
            {
                "description_translated": {"en": "Weekdays 08:30-16:30"},
                "frequency": "http://publications.europa.eu/resource/authority/frequency/DAILY",
            }
        ]
        assert hdab["special_opening_hours"] == [{"description_translated": {"en": "Closed on holidays"}}]

    def test_the_custodian_and_the_coordinator_are_parsed(self):
        dataset = parse(HDAB_TTL)

        assert dataset["hdab_coordinator"][0]["email"] == ["coordinator@example.org"]
        assert dataset["custodian"][0]["url"] == ["https://example.org/custodian"]
        assert dataset["custodian"][0]["name"] == "Custodian"

    def test_an_agent_without_a_contact_point_keeps_what_the_base_parse_gives(self):
        dataset = parse(
            AGENT_PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hdab <http://example.org/a> . '
            '<http://example.org/a> a foaf:Agent ; foaf:name "A" ; foaf:mbox <mailto:a@example.org> .'
        )

        (hdab,) = dataset["hdab"]
        assert hdab["email"] == ["a@example.org"]
        assert "telephone" not in hdab

    def test_several_contact_points_give_a_warning_and_the_first_is_read(self, caplog):
        with caplog.at_level(logging.WARNING):
            dataset = parse(
                AGENT_PREFIXES
                + '<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hdab <http://example.org/a> . '
                '<http://example.org/a> a foaf:Agent ; foaf:name "A" ; cv:contactPoint [ cv:email "a@example.org" ] , [ cv:email "b@example.org" ] .'
            )

        assert dataset["hdab"][0]["email"] in (["a@example.org"], ["b@example.org"])
        assert any("cv:contactPoint" in r.getMessage() for r in caplog.records)

    AGENT = {
        "uri": "http://example.org/hdab",
        "name": "Belgian HDAB",
        "name_translated": {"en": "Belgian HDAB"},
        "email": ["hdab@example.org"],
        "url": ["https://example.org/contact"],
        "telephone": ["+32 2 555 0102"],
        "opening_hours": [
            {
                "description_translated": {"en": "Weekdays 08:30-16:30"},
                "frequency": "http://publications.europa.eu/resource/authority/frequency/DAILY",
            }
        ],
        "special_opening_hours": [{"description_translated": {"en": "Closed on holidays"}}],
    }

    def test_each_health_agent_gets_exactly_one_contact_point(self):
        graph = serialize(
            {
                "hdab": [self.AGENT],
                "custodian": [{**self.AGENT, "uri": "http://example.org/custodian"}],
                "hdab_coordinator": [{**self.AGENT, "uri": "http://example.org/coordinator"}],
            }
        )

        for predicate in (HEALTHDCATAP.hdab, GEODCATAP.custodian, HEALTHDCATAP.hdabCoordinator):
            (agent,) = values(graph, predicate)
            (contact_point,) = values(graph, CV.contactPoint, agent)
            assert (contact_point, RDF.type, CV.ContactPoint) in graph

    def test_an_agent_in_two_roles_still_has_one_contact_point(self):
        graph = serialize({"hdab": [self.AGENT], "custodian": [self.AGENT]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, GEODCATAP.custodian) == [agent]
        assert len(values(graph, CV.contactPoint, agent)) == 1

    def test_the_contact_point_holds_the_email_the_page_and_the_telephone(self):
        graph = serialize({"hdab": [self.AGENT]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        (contact_point,) = values(graph, CV.contactPoint, agent)
        assert values(graph, CV.email, contact_point) == [Literal("hdab@example.org")]
        assert values(graph, CV.contactPage, contact_point) == [URIRef("https://example.org/contact")]
        assert values(graph, CV.telephone, contact_point) == [Literal("+32 2 555 0102")]

    def test_the_flat_vcard_and_foaf_terms_are_not_written(self):
        graph = serialize({"hdab": [self.AGENT]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, VCARD.hasEmail, agent) == []
        assert values(graph, FOAF.homepage, agent) == []

    def test_the_agent_keeps_its_name(self):
        graph = serialize({"hdab": [self.AGENT]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, FOAF.name, agent) == [Literal("Belgian HDAB", lang="en")]

    def test_the_health_dcat_ap_profile_still_writes_the_flat_terms(self):
        graph = serialize({"hdab": [self.AGENT]}, EuropeanHealthDCATAPProfile)

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, VCARD.hasEmail, agent)
        assert values(graph, CV.contactPoint, agent) == []

    def test_an_agent_without_contact_data_gets_no_contact_point(self):
        graph = serialize({"hdab": [{"uri": "http://example.org/hdab", "name": "Belgian HDAB"}]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, CV.contactPoint, agent) == []

    def test_an_agent_without_a_uri_gets_a_blank_node_with_its_contact_point(self):
        graph = serialize({"hdab": [{"name": "Anonymous", "email": "x@example.org"}]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, CV.contactPoint, agent)

    def test_the_opening_hours_are_temporal_entities(self):
        graph = serialize({"hdab": [self.AGENT]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        (contact_point,) = values(graph, CV.contactPoint, agent)
        (hours,) = values(graph, CV.openingHours, contact_point)
        (special,) = values(graph, CV.specialOpeningHoursSpecification, contact_point)
        assert (hours, RDF.type, TIME.TemporalEntity) in graph
        assert values(graph, DCT.description, hours) == [Literal("Weekdays 08:30-16:30", lang="en")]
        frequency = URIRef("http://publications.europa.eu/resource/authority/frequency/DAILY")
        assert values(graph, CV.frequency, hours) == [frequency]
        assert (frequency, RDF.type, DCT.Frequency) in graph
        assert values(graph, DCT.description, special) == [Literal("Closed on holidays", lang="en")]

    def test_the_parse_of_the_serialization_gives_the_agent_back(self):
        graph = serialize({"hdab": [self.AGENT]})

        (parsed,) = _profile(graph).parse_dataset({"extras": []}, DATASET)["hdab"]

        for key in ("email", "url", "telephone", "opening_hours", "special_opening_hours", "name"):
            assert parsed[key] == self.AGENT[key], key


class TestPublisherNote:
    def test_the_note_is_written_on_dct_description_for_every_language(self):
        graph = serialize(
            {"publisher": [{"uri": "http://example.org/p", "name": "P", "email": "p@example.org",
                            "publisher_note": {"en": "Maintained quarterly", "nl": "Elk kwartaal"}}]}
        )

        (publisher,) = values(graph, DCT.publisher)
        assert values(graph, DCT.description, publisher) == [
            Literal("Elk kwartaal", lang="nl"),
            Literal("Maintained quarterly", lang="en"),
        ] or sorted(values(graph, DCT.description, publisher), key=str) == sorted(
            [Literal("Maintained quarterly", lang="en"), Literal("Elk kwartaal", lang="nl")], key=str
        )
        assert values(graph, HEALTHDCATAP.publisherNote, publisher) == []

    def test_the_health_dcat_ap_profile_writes_the_legacy_predicate(self):
        graph = serialize(
            {"publisher": [{"uri": "http://example.org/p", "name": "P", "publisher_note": {"en": "Note"}}]},
            EuropeanHealthDCATAPProfile,
        )

        (publisher,) = values(graph, DCT.publisher)
        assert values(graph, HEALTHDCATAP.publisherNote, publisher) == [Literal("Note", lang="en")]

    def test_dct_description_is_read_as_the_note(self):
        graph = Graph().parse(
            data=AGENT_PREFIXES + '<http://example.org/dataset> dct:publisher <http://example.org/p> . '
            '<http://example.org/p> a foaf:Agent ; foaf:name "P" ; dct:description "Maintained quarterly"@en .',
            format="turtle",
        )

        (publisher,) = _profile(graph)._agents_details(DATASET, DCT.publisher)

        assert publisher["publisher_note"]["en"] == "Maintained quarterly"

    def test_only_the_publisher_reads_dct_description_as_a_note(self):
        graph = Graph().parse(
            data=AGENT_PREFIXES + '<http://example.org/dataset> healthdcatap:hdab <http://example.org/p> . '
            '<http://example.org/p> a foaf:Agent ; foaf:name "P" ; dct:description "Not a note"@en .',
            format="turtle",
        )

        (hdab,) = _profile(graph)._agents_details(DATASET, HEALTHDCATAP.hdab)

        assert "publisher_note" not in hdab or not any(hdab["publisher_note"].values())


VARIABLES_TTL = AGENT_PREFIXES + """
@prefix csvw: <http://www.w3.org/ns/csvw#> .
<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hasVariables <http://example.org/vars> .
<http://example.org/vars> a csvw:TableGroup ; dct:title "Variables"@en ; csvw:table <http://example.org/table> .
<http://example.org/table> a csvw:Table ; dct:title "Inventory"@en ; dcat:keyword "oncology"@en , "csvw"@en ;
    csvw:url <https://example.org/variables.csv> ; csvw:column <http://example.org/c1> , <http://example.org/c2> .
<http://example.org/c1> a csvw:Column ; csvw:name "patientId" ; csvw:title "Patient identifier"@en ;
    csvw:datatype "string" ; dct:description "Pseudonymised identifier"@en ; csvw:propertyUrl <http://purl.org/dc/terms/identifier> .
<http://example.org/c2> a csvw:Column ; csvw:name "alive" ; csvw:title "Alive"@en ; csvw:datatype "boolean" ;
    dct:description "Vital status"@en .
"""


class TestVariables:
    def test_the_table_group_is_parsed_with_its_tables_and_columns(self):
        (group,) = parse(VARIABLES_TTL)["variables"]

        assert group["title_translated"] == {"en": "Variables"}
        (table,) = group["tables"]
        assert table["title_translated"] == {"en": "Inventory"}
        assert table["keyword"] == ["csvw", "oncology"]
        assert table["url"] == "https://example.org/variables.csv"
        first, second = table["columns"]
        assert first["name"] == "alive" and second["name"] == "patientId"
        assert second["title_translated"] == {"en": "Patient identifier"}
        assert second["description_translated"] == {"en": "Pseudonymised identifier"}
        assert second["datatype"] == "string"
        assert second["property_url"] == "http://purl.org/dc/terms/identifier"
        assert "property_url" not in first

    def test_a_dataset_without_variables_has_no_field(self):
        assert "variables" not in parse(PREFIXES + "<http://example.org/dataset> a dcat:Dataset .")

    def test_the_serialization_is_a_csvw_table_group(self):
        graph = serialize({"variables": parse(VARIABLES_TTL)["variables"]})

        (group,) = values(graph, HEALTHDCATAP.hasVariables)
        assert (group, RDF.type, CSVW.TableGroup) in graph
        assert values(graph, DCT.title, group) == [Literal("Variables", lang="en")]
        (table,) = values(graph, CSVW.table, group)
        assert (table, RDF.type, CSVW.Table) in graph
        assert values(graph, CSVW.url, table) == [URIRef("https://example.org/variables.csv")]
        columns = values(graph, CSVW.column, table)
        assert len(columns) == 2 and all((c, RDF.type, CSVW.Column) in graph for c in columns)
        patient = next(c for c in columns if Literal("patientId") in graph.objects(c, CSVW.name))
        assert values(graph, CSVW.title, patient) == [Literal("Patient identifier", lang="en")]
        assert values(graph, DCT.description, patient) == [Literal("Pseudonymised identifier", lang="en")]
        assert values(graph, CSVW.propertyUrl, patient) == [URIRef("http://purl.org/dc/terms/identifier")]

    def test_the_parse_of_the_serialization_gives_the_variables_back(self):
        variables = parse(VARIABLES_TTL)["variables"]

        graph = serialize({"variables": variables})

        assert _profile(graph).parse_dataset({"extras": []}, DATASET)["variables"] == variables

    def test_variables_may_be_a_json_string(self):
        graph = serialize({"variables": '[{"title_translated": {"en": "V"}, "tables": []}]'})

        (group,) = values(graph, HEALTHDCATAP.hasVariables)
        assert values(graph, DCT.title, group) == [Literal("V", lang="en")]


class TestDistributionsAndDataServices:
    SERVICE = {
        "uri": "http://example.org/service",
        "title": "Access service",
        "documentation": ["https://example.org/docs"],
        "access_rights": "http://publications.europa.eu/resource/authority/access-right/RESTRICTED",
    }

    def _distribution(self, **extra):
        return {
            "resources": [
                {"id": "r1", "uri": "http://example.org/dist", "url": "http://example.org/file", **extra}
            ]
        }

    def test_the_data_service_documentation_is_written_as_foaf_page(self):
        graph = serialize(self._distribution(access_services=[self.SERVICE]))

        assert values(graph, FOAF.page, URIRef("http://example.org/service")) == [URIRef("https://example.org/docs")]

    def test_the_documentation_is_written_for_a_service_without_a_uri(self):
        service = {"title": "Anonymous", "documentation": ["https://example.org/docs"]}

        graph = serialize(self._distribution(access_services=[service]))

        (node,) = values(graph, DCAT.accessService, URIRef("http://example.org/dist"))
        assert values(graph, FOAF.page, node) == [URIRef("https://example.org/docs")]

    def test_the_access_rights_iri_of_a_data_service_is_a_rights_statement(self):
        graph = serialize(self._distribution(access_services=[self.SERVICE]))

        assert (
            URIRef("http://publications.europa.eu/resource/authority/access-right/RESTRICTED"),
            RDF.type,
            DCT.RightsStatement,
        ) in graph

    def test_free_text_access_rights_become_a_labelled_rights_statement_node(self):
        service = {**self.SERVICE, "access_rights": "Only for approved researchers"}

        graph = serialize(self._distribution(access_services=[service]))

        (statement,) = values(graph, DCT.accessRights, URIRef("http://example.org/service"))
        assert (statement, RDF.type, DCT.RightsStatement) in graph
        assert values(graph, RDFS.label, statement) == [Literal("Only for approved researchers")]

    def test_a_plain_format_becomes_a_labelled_node(self):
        graph = serialize(self._distribution(format="CSV", mimetype="text/csv"))

        (fmt,) = values(graph, DCT["format"], URIRef("http://example.org/dist"))
        (media_type,) = values(graph, DCAT.mediaType, URIRef("http://example.org/dist"))
        assert (fmt, RDF.type, DCT.MediaTypeOrExtent) in graph
        assert values(graph, RDFS.label, fmt) == [Literal("CSV")]
        assert (media_type, RDF.type, DCT.MediaType) in graph
        assert values(graph, RDFS.label, media_type) == [Literal("text/csv")]

    def test_a_format_iri_stays_an_iri(self):
        iri = "http://publications.europa.eu/resource/authority/file-type/CSV"

        graph = serialize(self._distribution(format=iri))

        assert values(graph, DCT["format"], URIRef("http://example.org/dist")) == [URIRef(iri)]

    def test_the_health_dcat_ap_profile_still_writes_a_plain_format(self):
        graph = serialize(self._distribution(format="CSV"), EuropeanHealthDCATAPProfile)

        assert values(graph, DCT["format"], URIRef("http://example.org/dist")) == [Literal("CSV")]

    def test_the_documentation_of_a_data_service_is_parsed(self):
        ttl = AGENT_PREFIXES + """
        <http://example.org/dataset> a dcat:Dataset ; dcat:distribution <http://example.org/dist> .
        <http://example.org/dist> a dcat:Distribution ; dcat:accessURL <http://example.org/file> ;
            dcat:accessService <http://example.org/service> .
        <http://example.org/service> a dcat:DataService ; dct:title "Service" ;
            foaf:page <https://example.org/docs> ; dcat:endpointURL <http://example.org/endpoint> .
        """

        (resource,) = parse(ttl)["resources"]

        (service,) = json.loads(resource["access_services"]) if isinstance(resource["access_services"], str) else resource["access_services"]
        assert service["documentation"] == ["https://example.org/docs"]

    def test_several_access_urls_give_a_warning(self, caplog):
        ttl = AGENT_PREFIXES + """
        <http://example.org/dataset> a dcat:Dataset ; dcat:distribution <http://example.org/dist> .
        <http://example.org/dist> a dcat:Distribution ; dcat:accessURL <http://example.org/f1> , <http://example.org/f2> .
        """

        with caplog.at_level(logging.WARNING):
            parse(ttl)

        assert any("resources.access_url" in r.getMessage() for r in caplog.records)


class TestWhatTheSchemaHasNoSubfieldFor:
    """With gdi_current listed first its narrower agent and data service fields win."""

    def test_the_contact_point_subfields_are_dropped_when_the_schema_lacks_them(self):
        narrow = {
            **SCHEMA,
            "dataset_fields": [
                _field("hdab", repeating_subfields=_agent_subfields()) if f["field_name"] == "hdab" else f
                for f in SCHEMA["dataset_fields"]
            ],
        }
        graph = Graph().parse(data=HDAB_TTL, format="turtle")
        with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: narrow):
            (hdab,) = EuropeanHealthDCATAPR8Profile(graph).parse_dataset({"extras": []}, DATASET)["hdab"]

        assert hdab["email"] == ["hdab@example.org"]
        assert not set(CONTACT_POINT) & set(hdab)

    def test_the_subfields_are_kept_when_the_schema_has_them(self):
        (hdab,) = parse(HDAB_TTL)["hdab"]

        assert set(CONTACT_POINT) <= set(hdab)


HDEU = "https://hdeu-dcat.data.health.europa.eu/resource/authority"


class TestVocabularyIris:
    """R8 wants the health vocabularies under one host; a bare authority code gets its IRI."""

    @pytest.mark.parametrize(
        "key, predicate, vocabulary, code",
        [
            ("health_category", HEALTHDCATAP.healthCategory, "healthcategories", "EHRS"),
            ("health_theme", HEALTHDCATAP.healthTheme, "health-theme", "HEALTH_SYSTEMS"),
            ("coding_system", HEALTHDCATAP.hasCodingSystem, "coding-system", "SNOMED-CT"),
            ("conforms_to", DCT.conformsTo, "standard", "DICOM"),
        ],
    )
    def test_a_bare_code_becomes_the_iri_in_its_vocabulary(self, key, predicate, vocabulary, code):
        graph = serialize({key: [code]})

        assert values(graph, predicate) == [URIRef(f"{HDEU}/{vocabulary}/{code}")]

    @pytest.mark.parametrize("key, predicate", [("coding_system", HEALTHDCATAP.hasCodingSystem), ("conforms_to", DCT.conformsTo)])
    def test_an_expanded_standard_is_typed(self, key, predicate):
        graph = serialize({key: ["DICOM"]})

        (iri,) = values(graph, predicate)
        assert (iri, RDF.type, DCT.Standard) in graph

    @pytest.mark.parametrize(
        "key, predicate",
        [
            ("health_category", HEALTHDCATAP.healthCategory),
            ("health_theme", HEALTHDCATAP.healthTheme),
            ("coding_system", HEALTHDCATAP.hasCodingSystem),
        ],
    )
    def test_an_iri_is_left_alone_whatever_its_host(self, key, predicate):
        for iri in ("http://www.wikidata.org/entity/Q12136", f"{HDEU}/other/ABC", "http://purl.org/adms/x"):
            assert URIRef(iri) in values(serialize({key: [iri]}), predicate)

    @pytest.mark.parametrize("text", ["Electronic health records", "ehrs", "EHR records", "Cancer"])
    def test_a_value_that_is_not_shaped_like_a_code_is_left_alone(self, text):
        graph = serialize({"health_category": [text]})

        (node,) = values(graph, HEALTHDCATAP.healthCategory)
        assert not str(node).startswith(HDEU)
        assert values(graph, SKOS.prefLabel, node) == [Literal(text)]

    @pytest.mark.parametrize("role", ["hdab", "custodian", "hdab_coordinator", "publisher"])
    def test_a_publisher_type_code_becomes_an_iri_on_every_agent(self, role):
        predicate = {
            "hdab": HEALTHDCATAP.hdab,
            "custodian": GEODCATAP.custodian,
            "hdab_coordinator": HEALTHDCATAP.hdabCoordinator,
            "publisher": DCT.publisher,
        }[role]

        graph = serialize({role: [{"uri": "http://example.org/a", "name": "A", "type": "non-gov-org"}]})

        (agent,) = values(graph, predicate)
        assert values(graph, DCT.type, agent) == [URIRef(f"{HDEU}/publisher-type/non-gov-org")]

    def test_a_publisher_type_iri_is_left_alone(self):
        iri = "http://purl.org/adms/publishertype/NonProfitOrganisation"

        graph = serialize({"hdab": [{"uri": "http://example.org/a", "name": "A", "type": iri}]})

        (agent,) = values(graph, HEALTHDCATAP.hdab)
        assert values(graph, DCT.type, agent) == [URIRef(iri)]

    def test_a_health_activity_type_code_becomes_an_iri(self):
        graph = serialize({"was_generated_by": [{"uri": "http://example.org/act", "dct_type": "ROUTINE_RECORDS"}]})

        assert values(graph, DCT.type, URIRef("http://example.org/act")) == [
            URIRef(f"{HDEU}/health-activity/ROUTINE_RECORDS")
        ]

    def test_a_health_activity_type_iri_is_left_alone(self):
        iri = f"{HDEU}/health-activity/ROUTINE_RECORDS"

        graph = serialize({"was_generated_by": [{"uri": "http://example.org/act", "dct_type": iri}]})

        assert values(graph, DCT.type, URIRef("http://example.org/act")) == [URIRef(iri)]

    def test_the_health_dcat_ap_profile_does_not_expand_codes(self):
        graph = serialize({"health_category": ["EHRS"]}, EuropeanHealthDCATAPProfile)

        assert values(graph, HEALTHDCATAP.healthCategory) == [Literal("EHRS")]


CONTACT_TTL = PREFIXES + """
@prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
<http://example.org/dataset> a dcat:Dataset ;
    dcat:contactPoint [ a vcard:Kind ; vcard:hasURL <https://example.org/support> ;
                        vcard:hasEmail <mailto:support@example.org> ] .
"""

# gdi_current lists the urls of a contact, so with it listed first the field keeps its list
LISTED_URLS_SCHEMA = {
    **SCHEMA,
    "dataset_fields": [
        _field("contact", repeating_subfields=[
            _field("email"),
            _field("url", preset="multiple_text", validators="ignore_missing scheming_multiple_text"),
        ])
    ],
}


def contact_urls(graph):
    (contact,) = values(graph, DCAT.contactPoint)
    return values(graph, VCARD.hasURL, contact)


class TestContactPage:
    """vcard:Kind has at most one vcard:hasURL in R8 (Kind_Shape), the contact page."""

    def test_the_contact_page_is_parsed_as_one_value(self):
        (contact,) = parse(CONTACT_TTL)["contact"]

        assert contact["url"] == "https://example.org/support"
        assert contact["email"] == "support@example.org"

    def test_a_contact_without_a_page_has_an_empty_url(self):
        ttl = PREFIXES + """
        @prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
        <http://example.org/dataset> a dcat:Dataset ;
            dcat:contactPoint [ a vcard:Kind ; vcard:hasEmail <mailto:support@example.org> ] .
        """

        (contact,) = parse(ttl)["contact"]

        assert not contact["url"]

    def test_a_schema_that_lists_the_urls_keeps_the_list(self):
        (contact,) = parse(CONTACT_TTL, schema=LISTED_URLS_SCHEMA)["contact"]

        assert contact["url"] == ["https://example.org/support"]

    def test_one_url_is_serialized_once(self):
        graph = serialize({"contact": [{"email": "a@example.org", "url": "https://example.org/a"}]})

        assert contact_urls(graph) == [URIRef("https://example.org/a")]

    def test_a_list_of_urls_is_written_as_the_first_one_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            graph = serialize({"contact": [{"email": "a@example.org", "url": ["https://example.org/a", "https://example.org/b"]}]})

        assert contact_urls(graph) == [URIRef("https://example.org/a")]
        assert any("only the first is kept" in record.getMessage() for record in caplog.records)

    def test_a_schema_that_lists_the_urls_writes_all_of_them(self):
        graph = serialize(
            {"contact": [{"email": "a@example.org", "url": ["https://example.org/a", "https://example.org/b"]}]},
            schema=LISTED_URLS_SCHEMA,
        )

        assert len(contact_urls(graph)) == 2

    def test_the_health_dcat_ap_profile_still_writes_every_url(self):
        graph = serialize(
            {"contact": [{"email": "a@example.org", "url": ["https://example.org/a", "https://example.org/b"]}]},
            EuropeanHealthDCATAPProfile,
        )

        assert len(contact_urls(graph)) == 2


POLICY_TTL = PREFIXES + """
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
<http://example.org/dataset> a dcat:Dataset ; dcat:distribution <http://example.org/dist> .
<http://example.org/dist> a dcat:Distribution ;
    dcat:accessURL <http://example.org/access> ;
    %s .
"""
DIST = URIRef("http://example.org/dist")


def policies(graph):
    return values(graph, ODRL.hasPolicy, DIST)


class TestDistributionPolicy:
    """odrl:hasPolicy (0..1) of a Distribution, kept as the IRI of the policy."""

    def test_the_policy_iri_is_parsed_into_has_policy(self):
        (resource,) = parse(POLICY_TTL % "odrl:hasPolicy <http://example.org/policy>")["resources"]

        assert resource["has_policy"] == "http://example.org/policy"

    def test_a_distribution_without_a_policy_has_no_field(self):
        (resource,) = parse(POLICY_TTL % "dct:title \"d\"")["resources"]

        assert "has_policy" not in resource

    def test_a_blank_node_policy_is_dropped_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            (resource,) = parse(POLICY_TTL % "odrl:hasPolicy [ a odrl:Policy ]")["resources"]

        assert "has_policy" not in resource
        assert any("blank node" in record.getMessage() for record in caplog.records)

    def test_several_policies_give_a_warning_and_the_first_iri(self, caplog):
        with caplog.at_level(logging.WARNING):
            (resource,) = parse(
                POLICY_TTL % "odrl:hasPolicy <http://example.org/policy-b>, <http://example.org/policy-a>"
            )["resources"]

        assert resource["has_policy"] == "http://example.org/policy-a"
        assert any("only the first is kept" in record.getMessage() for record in caplog.records)

    def test_the_policy_is_serialized_as_an_iri(self):
        graph = serialize({"resources": [{"id": "r1", "uri": str(DIST), "has_policy": "http://example.org/policy"}]})

        assert policies(graph) == [URIRef("http://example.org/policy")]
        assert {prefix: str(namespace) for prefix, namespace in graph.namespaces()}["odrl"] == str(ODRL)

    def test_a_value_that_is_not_an_iri_is_not_serialized(self, caplog):
        with caplog.at_level(logging.WARNING):
            graph = serialize({"resources": [{"id": "r1", "uri": str(DIST), "has_policy": "free text"}]})

        assert policies(graph) == []
        assert any("is not an IRI" in record.getMessage() for record in caplog.records)

    def test_an_empty_policy_writes_nothing(self):
        graph = serialize({"resources": [{"id": "r1", "uri": str(DIST), "has_policy": ""}]})

        assert policies(graph) == []

    def test_the_parse_of_the_serialization_gives_the_policy_back(self):
        graph = serialize({"resources": [{"id": "r1", "uri": str(DIST), "has_policy": "http://example.org/policy"}]})
        graph.add((DATASET, RDF.type, DCAT.Dataset))
        graph.add((DATASET, DCAT.distribution, DIST))

        (resource,) = _profile(graph).parse_dataset({"extras": []}, DATASET)["resources"]

        assert resource["has_policy"] == "http://example.org/policy"

    def test_the_health_dcat_ap_profile_does_not_write_the_policy(self):
        graph = serialize(
            {"resources": [{"id": "r1", "uri": str(DIST), "has_policy": "http://example.org/policy"}]},
            EuropeanHealthDCATAPProfile,
        )

        assert policies(graph) == []


RETENTION_TTL = POLICY_TTL % """healthdcatap:retentionPeriod [ a dct:PeriodOfTime ;
        dcat:startDate "2020-01-01"^^xsd:date ; dcat:endDate "2030-01-01"^^xsd:date ]"""


class TestDistributionKeys:
    """What a distribution keeps after the parse is what R8 defines on it."""

    def test_the_retention_period_of_a_distribution_is_not_read(self):
        (resource,) = parse(RETENTION_TTL)["resources"]

        assert "retention_period" not in resource

    def test_the_health_dcat_ap_profile_still_reads_it(self):
        (resource,) = parse(RETENTION_TTL, EuropeanHealthDCATAPProfile)["resources"]

        assert resource["retention_period"]

    def test_the_link_to_the_distribution_node_is_not_kept(self):
        (resource,) = parse(POLICY_TTL % "dct:title \"d\"")["resources"]

        assert "distribution_ref" not in resource

    def test_the_policy_is_read_before_the_link_is_dropped(self):
        (resource,) = parse(POLICY_TTL % "odrl:hasPolicy <http://example.org/policy>")["resources"]

        assert resource["has_policy"] == "http://example.org/policy"
        assert "distribution_ref" not in resource

    def test_a_retention_period_of_a_resource_is_not_serialized(self):
        resource = {"id": "r1", "uri": str(DIST), "retention_period": [{"start": "2020-01-01", "end": "2030-01-01"}]}

        graph = serialize({"resources": [resource]})

        assert values(graph, HEALTHDCATAP.retentionPeriod, DIST) == []

    def test_the_health_dcat_ap_profile_still_serializes_it(self):
        resource = {"id": "r1", "uri": str(DIST), "retention_period": [{"start": "2020-01-01", "end": "2030-01-01"}]}

        graph = serialize({"resources": [resource]}, EuropeanHealthDCATAPProfile)

        assert values(graph, HEALTHDCATAP.retentionPeriod, DIST)

    def test_the_retention_period_of_the_dataset_is_still_serialized(self):
        graph = serialize({"retention_period": [{"start": "2020-01-01", "end": "2030-01-01"}], "resources": []})

        assert values(graph, HEALTHDCATAP.retentionPeriod)


MANY_TTL = AGENT_PREFIXES + """
<http://example.org/dataset> a dcat:Dataset ; healthdcatap:hdab <http://example.org/hdab> .
<http://example.org/hdab> a foaf:Agent ; foaf:name "HDAB" ;
    cv:contactPoint [ a cv:ContactPoint ;
        cv:email "b@example.org", "a@example.org" ;
        cv:contactPage <https://example.org/page-b>, <https://example.org/page-a> ;
        cv:telephone "+32 2 555 0102", "+32 2 555 0101" ] .
"""


def single_valued_schema():
    """An agent whose email, contact page and telephone hold one value (the gdi_current agent)."""
    plain = [_field(n) for n in ("uri", "name", "name_translated", "email", "url", "type", "publisher_note", *CONTACT_POINT)]
    return {
        **SCHEMA,
        "dataset_fields": [
            _field(f["field_name"], repeating_subfields=plain) if f["field_name"] in ("publisher", "hdab") else f
            for f in SCHEMA["dataset_fields"]
        ],
    }


class TestContactPointCardinality:
    """cv:ContactPoint: cv:email, cv:contactPage and cv:telephone are 0..n (R8, Contact point)."""

    def test_every_email_page_and_telephone_is_read_in_a_fixed_order(self):
        (hdab,) = parse(MANY_TTL)["hdab"]

        assert hdab["email"] == ["a@example.org", "b@example.org"]
        assert hdab["url"] == ["https://example.org/page-a", "https://example.org/page-b"]
        assert hdab["telephone"] == ["+32 2 555 0101", "+32 2 555 0102"]

    def test_every_value_is_serialized_on_the_one_contact_point(self):
        agent = {
            "uri": "http://example.org/hdab",
            "name": "HDAB",
            "email": ["a@example.org", "b@example.org"],
            "url": ["https://example.org/page-a", "https://example.org/page-b"],
            "telephone": ["+32 2 555 0101", "+32 2 555 0102"],
        }

        graph = serialize({"hdab": [agent]})

        (contact_point,) = values(graph, CV.contactPoint, URIRef("http://example.org/hdab"))
        assert values(graph, CV.email, contact_point) == [Literal("a@example.org"), Literal("b@example.org")]
        assert values(graph, CV.contactPage, contact_point) == [
            URIRef("https://example.org/page-a"),
            URIRef("https://example.org/page-b"),
        ]
        assert len(values(graph, CV.telephone, contact_point)) == 2

    def test_a_single_value_is_serialized_as_before(self):
        agent = {"uri": "http://example.org/hdab", "name": "HDAB", "email": "a@example.org", "telephone": "123"}

        graph = serialize({"hdab": [agent]})

        (contact_point,) = values(graph, CV.contactPoint, URIRef("http://example.org/hdab"))
        assert values(graph, CV.email, contact_point) == [Literal("a@example.org")]
        assert values(graph, CV.telephone, contact_point) == [Literal("123")]

    def test_a_schema_that_holds_one_value_keeps_the_first_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            (hdab,) = parse(MANY_TTL, schema=single_valued_schema())["hdab"]

        assert hdab["email"] == "a@example.org"
        assert hdab["url"] == "https://example.org/page-a"
        assert any("holds one" in record.getMessage() for record in caplog.records)

    def test_the_parse_of_the_serialization_gives_all_values_back(self):
        (hdab,) = parse(MANY_TTL)["hdab"]

        graph = serialize({"hdab": [hdab]})
        graph.add((DATASET, RDF.type, DCAT.Dataset))
        graph.add((DATASET, HEALTHDCATAP.hdab, URIRef(hdab["uri"])))
        (again,) = _profile(graph).parse_dataset({"extras": []}, DATASET)["hdab"]

        for key in ("email", "url", "telephone"):
            assert again[key] == hdab[key], key



RELATIONSHIP_TTL = PREFIXES + """
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://example.org/dataset> a dcat:Dataset ;
    dcat:qualifiedRelation <http://example.org/rel> .
<http://example.org/rel> a dcat:Relationship ;
    dct:relation <http://example.org/other-b>, <http://example.org/other-a> ;
    dcat:hadRole <http://example.org/role-b>, <http://example.org/role-a> .
"""


def single_relation_schema():
    """A relationship whose relation and role hold one value (the gdi_current one)."""
    plain = [_field(n) for n in ("uri", "relation", "role")]
    return {
        **SCHEMA,
        "dataset_fields": [
            _field("qualified_relation", repeating_subfields=plain) if f["field_name"] == "qualified_relation" else f
            for f in SCHEMA["dataset_fields"]
        ],
    }


class TestQualifiedRelationCardinality:
    """dcat:Relationship: dct:relation and dcat:hadRole are 1..n (R8, Relationship)."""

    def test_every_relation_and_role_is_parsed_sorted(self):
        (relation,) = parse(RELATIONSHIP_TTL)["qualified_relation"]

        assert relation["uri"] == "http://example.org/rel"
        assert relation["relation"] == ["http://example.org/other-a", "http://example.org/other-b"]
        assert relation["role"] == ["http://example.org/role-a", "http://example.org/role-b"]

    def test_a_schema_that_holds_one_value_gets_one_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            (relation,) = parse(RELATIONSHIP_TTL, schema=single_relation_schema())["qualified_relation"]

        assert isinstance(relation["relation"], str) and isinstance(relation["role"], str)
        messages = [record.getMessage() for record in caplog.records]
        assert any("qualified_relation.relation" in m for m in messages)
        assert any("qualified_relation.role" in m for m in messages)

    def test_a_list_valued_schema_does_not_warn(self, caplog):
        with caplog.at_level(logging.WARNING):
            parse(RELATIONSHIP_TTL)

        assert not [r for r in caplog.records if "qualified_relation" in r.getMessage()]

    def test_every_relation_and_role_is_written(self):
        graph = serialize(
            {
                "qualified_relation": [
                    {
                        "uri": "http://example.org/rel",
                        "relation": ["http://example.org/other-a", "a free text relation, with a comma"],
                        "role": ["http://example.org/role-a", "http://example.org/role-b"],
                    }
                ]
            }
        )
        rel = URIRef("http://example.org/rel")

        assert (DATASET, DCAT.qualifiedRelation, rel) in graph
        assert (rel, RDF.type, DCAT.Relationship) in graph
        assert [str(v) for v in values(graph, DCT.relation, rel)] == [
            "a free text relation, with a comma",
            "http://example.org/other-a",
        ]
        assert [str(v) for v in values(graph, DCAT.hadRole, rel)] == ["http://example.org/role-a", "http://example.org/role-b"]
        assert (URIRef("http://example.org/role-a"), RDF.type, DCAT.Role) in graph
        assert (URIRef("http://example.org/other-a"), RDF.type, RDFS.Resource) in graph

    def test_a_single_string_value_is_written_as_one_value(self):
        graph = serialize({"qualified_relation": [{"relation": "http://example.org/a, b", "role": "http://example.org/r"}]})
        (rel,) = graph.objects(DATASET, DCAT.qualifiedRelation)

        assert len(values(graph, DCT.relation, rel)) == 1
        assert len(values(graph, DCAT.hadRole, rel)) == 1

    def test_an_empty_relationship_is_not_written(self):
        graph = serialize({"qualified_relation": [{"uri": "", "relation": [], "role": []}]})

        assert not list(graph.objects(DATASET, DCAT.qualifiedRelation))

    def test_it_round_trips(self):
        (relation,) = parse(RELATIONSHIP_TTL)["qualified_relation"]
        again = parse(serialize({"qualified_relation": [relation]}).serialize(format="turtle"))["qualified_relation"]

        assert again == [relation]


ATTRIBUTION_TTL = PREFIXES + """
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
<http://example.org/dataset> a dcat:Dataset ;
    prov:qualifiedAttribution [
        a prov:Attribution ;
        prov:agent <http://example.org/agent> ;
        dcat:hadRole <http://example.org/role-b>, <http://example.org/role-a>
    ] .
<http://example.org/agent> a foaf:Agent ; foaf:name "Agent"@en .
"""


def single_role_schema():
    plain = [_field("agent"), _field("role")]
    return {
        **SCHEMA,
        "dataset_fields": [
            _field("qualified_attribution", repeating_subfields=plain) if f["field_name"] == "qualified_attribution" else f
            for f in SCHEMA["dataset_fields"]
        ],
    }


class TestQualifiedAttributionRoles:
    """prov:Attribution: dcat:hadRole is 1..n."""

    def test_every_role_is_parsed_sorted(self):
        (attribution,) = parse(ATTRIBUTION_TTL)["qualified_attribution"]

        assert attribution["role"] == ["http://example.org/role-a", "http://example.org/role-b"]
        assert attribution["agent"][0]["uri"] == "http://example.org/agent"

    def test_a_schema_that_holds_one_role_gets_the_first_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            (attribution,) = parse(ATTRIBUTION_TTL, schema=single_role_schema())["qualified_attribution"]

        assert attribution["role"] == "http://example.org/role-a"
        assert any("dcat:hadRole" in record.getMessage() for record in caplog.records)

    def test_every_role_and_the_agent_are_written(self):
        graph = serialize(
            {
                "qualified_attribution": [
                    {
                        "agent": [{"uri": "http://example.org/agent", "name": "Agent"}],
                        "role": ["http://example.org/role-a", "http://example.org/role-b"],
                    }
                ]
            }
        )
        (node,) = graph.objects(DATASET, PROV.qualifiedAttribution)

        assert (node, RDF.type, PROV.Attribution) in graph
        assert [str(v) for v in values(graph, DCAT.hadRole, node)] == ["http://example.org/role-a", "http://example.org/role-b"]
        assert (URIRef("http://example.org/role-a"), RDF.type, DCAT.Role) in graph
        assert (node, PROV.agent, URIRef("http://example.org/agent")) in graph

    def test_a_single_role_string_is_written_as_one_role(self):
        graph = serialize({"qualified_attribution": [{"agent": [], "role": "http://example.org/role-a"}]})
        (node,) = graph.objects(DATASET, PROV.qualifiedAttribution)

        assert len(values(graph, DCAT.hadRole, node)) == 1

    def test_an_empty_attribution_is_not_written(self):
        graph = serialize({"qualified_attribution": [{"agent": [], "role": []}]})

        assert not list(graph.objects(DATASET, PROV.qualifiedAttribution))

    def test_it_round_trips(self):
        (attribution,) = parse(ATTRIBUTION_TTL)["qualified_attribution"]
        again = parse(serialize({"qualified_attribution": [attribution]}).serialize(format="turtle"))["qualified_attribution"]

        assert [a["role"] for a in again] == [attribution["role"]]


class TestEveryValuePerLanguageIsKept:
    """Values in the same language are all kept: with dct:provenance 1..n none may be lost."""

    TTL = PREFIXES + """
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <http://example.org/dataset> a dcat:Dataset ;
        dct:provenance [ a dct:ProvenanceStatement ; rdfs:label "Second statement"@en ] ,
                       [ a dct:ProvenanceStatement ; rdfs:label "First statement"@en ] ,
                       [ a dct:ProvenanceStatement ; rdfs:label "Eerste verklaring"@nl ] .
    """

    def test_statements_in_one_language_are_all_kept_sorted(self, caplog):
        with caplog.at_level(logging.WARNING):
            provenance = _multilingual(self.TTL, DCT.provenance)

        assert provenance == {"en": "First statement\n\nSecond statement", "nl": "Eerste verklaring"}
        assert any("they are joined" in record.getMessage() for record in caplog.records)

    def test_one_value_per_language_is_unchanged_and_missing_form_languages_are_empty(self):
        ttl = PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; dct:title "Title"@en .'

        assert _multilingual(ttl, DCT.title) == {"en": "Title", "nl": ""}

    def test_a_value_without_a_language_is_in_the_default_language(self):
        ttl = PREFIXES + '<http://example.org/dataset> a dcat:Dataset ; dct:title "Plain" .'

        assert _multilingual(ttl, DCT.title)["en"] == "Plain"


def _multilingual(turtle, predicate):
    graph = Graph().parse(data=turtle, format="turtle")
    return _profile(graph)._object_value_multilingual(DATASET, predicate)
