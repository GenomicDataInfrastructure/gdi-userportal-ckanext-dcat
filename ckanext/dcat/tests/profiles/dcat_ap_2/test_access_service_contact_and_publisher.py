"""
The parser gives the contact and the publisher of a data service as lists of dicts, and
so do the repeating subfields of the schema. Serializing them used to raise
``AttributeError: 'list' object has no attribute 'get'`` and failed the whole dataset.
"""
import json

import pytest
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import DCTERMS as DCT
from rdflib.namespace import Namespace

from ckanext.dcat.profiles import EuropeanDCATAP2Profile

DCAT = Namespace("http://www.w3.org/ns/dcat#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

DATASET = URIRef("http://example.org/dataset")
DISTRIBUTION = URIRef("http://example.org/distribution")
SERVICE = URIRef("http://example.org/service")

CONTACT = {"name": "Service desk", "email": "desk@example.org", "url": ["https://example.org/desk"]}
PUBLISHER = {"name": "Service publisher", "email": "pub@example.org"}


def _serialize(**service):
    dataset = {
        "id": "1",
        "name": "test",
        "title": "Test dataset",
        "resources": [
            {
                "id": "r1",
                "uri": str(DISTRIBUTION),
                "url": "http://example.org/file",
                "access_services": json.dumps([{"uri": str(SERVICE), "title": "Service", **service}]),
            }
        ],
    }
    graph = Graph()
    EuropeanDCATAP2Profile(graph).graph_from_dataset(dataset, DATASET)
    return graph


@pytest.mark.parametrize("contact", [[CONTACT], CONTACT], ids=["list", "dict"])
def test_the_contact_of_a_data_service_is_serialized(contact):
    graph = _serialize(contact=contact)

    (contact_ref,) = graph.objects(SERVICE, DCAT.contactPoint)
    assert (contact_ref, RDF.type, VCARD.Kind) in graph
    assert list(graph.objects(contact_ref, VCARD.hasURL)) == [URIRef("https://example.org/desk")]


@pytest.mark.parametrize("publisher", [[PUBLISHER], PUBLISHER], ids=["list", "dict"])
def test_the_publisher_of_a_data_service_is_serialized(publisher):
    graph = _serialize(publisher=publisher)

    (publisher_ref,) = graph.objects(SERVICE, DCT.publisher)
    assert (publisher_ref, RDF.type, FOAF.Agent) in graph


def test_several_contacts_are_all_serialized():
    graph = _serialize(contact=[CONTACT, {"name": "Second desk", "email": "second@example.org"}])

    assert len(list(graph.objects(SERVICE, DCAT.contactPoint))) == 2


@pytest.mark.parametrize("empty", [None, [], {}, [{}], ""])
def test_an_empty_contact_or_publisher_writes_nothing(empty):
    graph = _serialize(contact=empty, publisher=empty)

    assert not list(graph.objects(SERVICE, DCAT.contactPoint))
    assert not list(graph.objects(SERVICE, DCT.publisher))
