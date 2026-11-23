"""
A value that is not an integer where the schema wants one is kept as it is, so that the schema rejects it
and the harvester can report it, instead of being dropped without a trace. Without a CKAN database.
"""
import os
from unittest import mock

import pytest
import yaml
from rdflib import Graph, URIRef

import ckanext.dcat
from ckanext.dcat.profiles import EuropeanHealthDCATAPProfile, base

SCHEMA_PATH = os.path.join(os.path.dirname(ckanext.dcat.__file__), "schemas", "health_dcat_ap.yaml")
DATASET = URIRef("http://example.org/dataset")

PREFIXES = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix healthdcatap: <http://healthdataportal.eu/ns/health#> .
"""


def _parse(body):
    turtle = f"""{PREFIXES}
<http://example.org/dataset> a dcat:Dataset ;
    dct:title "Test dataset" ;
    {body} .
"""
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    graph = Graph()
    graph.parse(data=turtle, format="turtle")

    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        return EuropeanHealthDCATAPProfile(graph).parse_dataset({"extras": []}, DATASET)


@pytest.mark.parametrize("key, predicate", [
    ("number_of_records", "numberOfRecords"),
    ("number_of_unique_individuals", "numberOfUniqueIndividuals"),
    ("min_typical_age", "minTypicalAge"),
    ("max_typical_age", "maxTypicalAge"),
])
class TestHealthIntegers:
    def test_a_number_is_read_as_an_integer(self, key, predicate):
        assert _parse(f'healthdcatap:{predicate} "1000"')[key] == 1000

    def test_a_value_that_is_not_a_number_is_kept_as_it_is(self, key, predicate):
        assert _parse(f'healthdcatap:{predicate} "about 1000"')[key] == "about 1000"

    def test_no_value_leaves_the_key_out(self, key, predicate):
        assert key not in _parse('dct:description "x"')


def test_zero_is_a_value():
    assert _parse('healthdcatap:numberOfRecords "0"')["number_of_records"] == 0


def test_a_byte_size_that_is_not_a_number_is_kept_as_it_is():
    turtle = 'dcat:distribution [ a dcat:Distribution ; dcat:byteSize "large" ]'

    assert _parse(turtle)["resources"][0]["size"] == "large"


def test_a_byte_size_that_is_a_number_is_an_integer():
    turtle = 'dcat:distribution [ a dcat:Distribution ; dcat:byteSize "2048" ]'

    assert _parse(turtle)["resources"][0]["size"] == 2048
