"""
Every dct:spatial of a dataset ends up in its spatial coverage, without a CKAN database.
"""
import os
from unittest import mock

import yaml
from rdflib import Graph, URIRef

import ckanext.dcat
from ckanext.dcat.profiles import EuropeanHealthDCATAPProfile, base

SCHEMA_PATH = os.path.join(
    os.path.dirname(ckanext.dcat.__file__), "schemas", "health_dcat_ap.yaml"
)

DATASET = URIRef("http://example.org/dataset")
COUNTRY = "http://publications.europa.eu/resource/authority/country/NLD"
PLACE = "http://publications.europa.eu/resource/authority/place/NLD_UTC"

PREFIXES = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
"""


def _spatial_coverage(spatial):
    turtle = f"""{PREFIXES}
<http://example.org/dataset> a dcat:Dataset ;
    dct:title "Test dataset" ;
    dct:spatial {spatial} .
"""
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    graph = Graph()
    graph.parse(data=turtle, format="turtle")

    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        dataset_dict = EuropeanHealthDCATAPProfile(graph).parse_dataset(
            {"extras": []}, DATASET
        )

    return dataset_dict["spatial_coverage"]


def test_a_country_and_a_place_are_both_in_the_spatial_coverage():
    spatial_coverage = _spatial_coverage(f"<{COUNTRY}> , <{PLACE}>")

    assert sorted(item["uri"] for item in spatial_coverage) == [COUNTRY, PLACE]


def test_a_location_keeps_its_label():
    spatial_coverage = _spatial_coverage(
        f'<{COUNTRY}> , [ a dct:Location ; skos:prefLabel "Utrecht" ]'
    )

    assert sorted(spatial_coverage, key=lambda item: "text" in item) == [
        {"uri": COUNTRY},
        {"text": "Utrecht"},
    ]
