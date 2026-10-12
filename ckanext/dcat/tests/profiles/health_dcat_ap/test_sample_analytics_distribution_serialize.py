"""
Samples and analytics are distributions that are linked by their own property only,
without a CKAN database.
"""
import os
from unittest import mock

import pytest
import yaml
from rdflib import Graph, URIRef
from rdflib.namespace import Namespace

import ckanext.dcat
from ckanext.dcat.profiles import EuropeanHealthDCATAPProfile, base

DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
HEALTHDCATAP = Namespace("http://healthdataportal.eu/ns/health#")

SCHEMA_PATH = os.path.join(
    os.path.dirname(ckanext.dcat.__file__), "schemas", "health_dcat_ap.yaml"
)

DATASET = URIRef("http://example.org/dataset")
DISTRIBUTION = "http://example.org/distribution"
SAMPLE = "http://example.org/sample"
ANALYTICS = "http://example.org/analytics"


@pytest.fixture
def graph():
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    dataset_dict = {
        "id": "1",
        "name": "test",
        "title": "Test dataset",
        "notes": "Test dataset",
        "distribution": [DISTRIBUTION],
        "sample": [SAMPLE],
        "analytics": [ANALYTICS],
        "resources": [
            {"id": "d", "uri": DISTRIBUTION, "url": "http://example.org/distribution/file"},
            {"id": "s", "uri": SAMPLE, "url": "http://example.org/sample/file"},
            {"id": "a", "uri": ANALYTICS, "url": "http://example.org/analytics/file"},
        ],
    }

    graph = Graph()
    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        EuropeanHealthDCATAPProfile(graph).graph_from_dataset(dataset_dict, DATASET)

    return graph


def test_each_distribution_is_linked_by_its_own_property_only(graph):
    objects = lambda predicate: sorted(str(o) for o in graph.objects(DATASET, predicate))

    assert objects(DCAT.distribution) == [DISTRIBUTION]
    assert objects(ADMS.sample) == [SAMPLE]
    assert objects(HEALTHDCATAP.analytics) == [ANALYTICS]


def test_parsing_the_serialization_gives_the_same_distribution_sample_and_analytics(graph):
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        parsed = EuropeanHealthDCATAPProfile(graph).parse_dataset({"extras": []}, DATASET)

    assert parsed["distribution"] == [DISTRIBUTION]
    assert parsed["sample"] == [SAMPLE]
    assert parsed["analytics"] == [ANALYTICS]
    assert sorted(r["uri"] for r in parsed["resources"]) == sorted(
        [DISTRIBUTION, SAMPLE, ANALYTICS]
    )
