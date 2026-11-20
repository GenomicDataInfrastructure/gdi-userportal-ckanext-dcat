"""
Every vcard:hasURL of a dataset contact ends up in the url list of that contact, without a CKAN
database.
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

PREFIXES = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix vcard: <http://www.w3.org/2006/vcard/ns#> .
"""


def _contact_urls(contact_properties):
    turtle = f"""{PREFIXES}
<http://example.org/dataset> a dcat:Dataset ;
    dct:title "Test dataset" ;
    dcat:contactPoint [
        a vcard:Kind ;
        vcard:fn "Contact" ;
        {contact_properties}
    ] .
"""
    with open(SCHEMA_PATH) as f:
        schema = yaml.safe_load(f)

    graph = Graph()
    graph.parse(data=turtle, format="turtle")

    with mock.patch.object(base, "get_action", lambda name: lambda ctx, data: schema):
        dataset_dict = EuropeanHealthDCATAPProfile(graph).parse_dataset(
            {"extras": []}, DATASET
        )

    (contact,) = dataset_dict["contact"]
    return contact["url"]


def test_every_contact_url_is_kept():
    urls = _contact_urls(
        "vcard:hasURL <https://a.example> , <https://b.example> , <https://c.example> ;"
    )

    assert sorted(urls) == ["https://a.example", "https://b.example", "https://c.example"]


def test_the_urls_come_out_in_a_stable_order():
    first = _contact_urls("vcard:hasURL <https://b.example> , <https://a.example> ;")
    second = _contact_urls("vcard:hasURL <https://a.example> , <https://b.example> ;")

    assert first == second == ["https://a.example", "https://b.example"]


def test_a_single_contact_url_stays_a_one_item_list():
    assert _contact_urls("vcard:hasURL <https://a.example> ;") == ["https://a.example"]


def test_a_contact_without_url_has_an_empty_list():
    assert _contact_urls('vcard:hasEmail <mailto:contact@example.org> ;') == []


def test_a_url_given_as_a_vcard_value_node_is_read():
    urls = _contact_urls(
        'vcard:hasURL [ vcard:hasValue <https://a.example> ] , <https://b.example> ;'
    )

    assert sorted(urls) == ["https://a.example", "https://b.example"]
