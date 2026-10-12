"""
Samples and analytics are parsed like any other distribution, without a CKAN database.
"""
import os
from unittest import mock

import pytest
import yaml
from rdflib import Graph, URIRef

import ckanext.dcat
from ckanext.dcat.profiles import EuropeanHealthDCATAPProfile, base

SCHEMA_PATH = os.path.join(
    os.path.dirname(ckanext.dcat.__file__), "schemas", "health_dcat_ap.yaml"
)

DATASET = URIRef("http://example.org/dataset")
NAMES = ("distribution", "sample", "analytics")
LANGUAGE = "http://publications.europa.eu/resource/authority/language"


def _distribution(name):
    return f"""
<http://example.org/{name}> a dcat:Distribution ;
    dcat:accessURL <http://example.org/{name}/access> ;
    dct:conformsTo <http://example.org/{name}/conformsTo1> ,
                   <http://example.org/{name}/conformsTo2> ;
    dct:language <{LANGUAGE}/ITA> , <{LANGUAGE}/SPA> ;
    dcatap:applicableLegislation <http://example.org/{name}/legislation> ;
    healthdcatap:retentionPeriod [ a dct:PeriodOfTime ;
        dcat:startDate "2024-01-01"^^xsd:date ;
        dcat:endDate "2025-01-01"^^xsd:date ] .
"""


TURTLE = (
    """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dcatap: <http://data.europa.eu/r5r/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix adms: <http://www.w3.org/ns/adms#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix healthdcatap: <http://healthdataportal.eu/ns/health#> .

<http://example.org/dataset> a dcat:Dataset ;
    dct:title "Test dataset" ;
    dcat:distribution <http://example.org/distribution> ;
    adms:sample <http://example.org/sample> ;
    healthdcatap:analytics <http://example.org/analytics> .
"""
    + "".join(_distribution(name) for name in NAMES)
)


@pytest.fixture(scope="module")
def resources():
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    graph = Graph()
    graph.parse(data=TURTLE, format="turtle")

    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        dataset_dict = EuropeanHealthDCATAPProfile(graph).parse_dataset(
            {"extras": []}, DATASET
        )

    return {r["uri"].rsplit("/", 1)[1]: r for r in dataset_dict["resources"]}


@pytest.mark.parametrize("name", NAMES)
def test_values_are_parsed_the_same_for_distribution_sample_and_analytics(resources, name):
    resource = resources[name]

    assert sorted(resource["conforms_to"]) == [
        f"http://example.org/{name}/conformsTo1",
        f"http://example.org/{name}/conformsTo2",
    ]
    assert sorted(resource["language"]) == [f"{LANGUAGE}/ITA", f"{LANGUAGE}/SPA"]
    assert resource["applicable_legislation"] == [f"http://example.org/{name}/legislation"]
    assert resource["retention_period"] == [{"start": "2024-01-01", "end": "2025-01-01"}]
