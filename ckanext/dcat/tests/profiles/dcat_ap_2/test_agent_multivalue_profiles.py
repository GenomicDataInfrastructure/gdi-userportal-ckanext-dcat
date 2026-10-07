"""
Agent identifier/country across profiles, without a CKAN database.

The scheming profile keeps writing URI identifiers as URI references (as before) and the
non-scheming profiles keep storing a single string per extra, even though the shared agent
parser now returns lists.
"""
import os
from unittest import mock

import pytest
import yaml
from rdflib import Graph, URIRef
from rdflib.namespace import Namespace

import ckanext.dcat
from ckanext.dcat.profiles import (
    EuropeanDCATAP2Profile,
    EuropeanDCATAPSchemingProfile,
    base,
)

DCT = Namespace("http://purl.org/dc/terms/")
DATASET = URIRef("http://example.org/dataset")
ROR = "https://ror.org/05wg1m734"
NLD = "http://publications.europa.eu/resource/authority/country/NLD"
DEU = "http://publications.europa.eu/resource/authority/country/DEU"

SCHEMA_PATH = os.path.join(
    os.path.dirname(ckanext.dcat.__file__), "schemas", "health_dcat_ap.yaml"
)


@pytest.fixture
def scheming_schema():
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)
    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        yield schema


def _serialise(agent):
    graph = Graph()
    EuropeanDCATAPSchemingProfile(graph).graph_from_dataset(
        {"id": "1", "name": "t", "title": "T", "publisher": [agent]}, DATASET
    )
    return graph


def _terms(graph, predicate):
    return sorted(
        (type(o).__name__, str(o))
        for s, o in graph.subject_objects(predicate)
        if str(o) in (ROR, "plain-id", NLD, DEU)
    )


@pytest.mark.usefixtures("scheming_schema")
class TestSchemingProfileAgentSerialization:

    def test_legacy_uri_identifier_stays_a_uri_reference(self):
        graph = _serialise({"name": "Org", "identifier": ROR})

        assert _terms(graph, DCT.identifier) == [("URIRef", ROR)]

    def test_uri_identifiers_in_a_list_are_uri_references_and_others_literals(self):
        graph = _serialise({"name": "Org", "identifier": [ROR, "plain-id"]})

        assert _terms(graph, DCT.identifier) == [("Literal", "plain-id"), ("URIRef", ROR)]

    def test_several_countries_become_one_triple_each(self):
        graph = _serialise({"name": "Org", "country": [NLD, DEU]})

        assert _terms(graph, DCT.spatial) == [("URIRef", DEU), ("URIRef", NLD)]

    def test_legacy_scalar_country_is_still_serialised(self):
        graph = _serialise({"name": "Org", "country": NLD})

        assert _terms(graph, DCT.spatial) == [("URIRef", NLD)]


class TestNonSchemingProfileExtras:
    TTL = """
    @prefix dct: <http://purl.org/dc/terms/> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix dcat: <http://www.w3.org/ns/dcat#> .
    <http://example.org/dataset> a dcat:Dataset ; dct:title "T" ;
        dct:publisher <http://example.org/org> .
    <http://example.org/org> a foaf:Organization ; foaf:name "Org" ;
        dct:identifier "%s" ; dct:spatial <%s> .
    """

    def test_agent_identifier_and_country_extras_are_plain_strings(self):
        graph = Graph()
        graph.parse(format="turtle", data=self.TTL % (ROR, NLD))
        dataset_dict = {"extras": [], "resources": []}

        EuropeanDCATAP2Profile(graph).parse_dataset(dataset_dict, DATASET)

        extras = {e["key"]: e["value"] for e in dataset_dict["extras"]}
        assert extras["publisher_identifier"] == ROR
        assert extras["publisher_country"] == NLD
