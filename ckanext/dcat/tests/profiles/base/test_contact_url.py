"""
The contact's url is a list when it comes from the parser or a multiple_text field,
and a string in older data. Either way it is written as one vcard:hasURL IRI per value.
"""
import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import Namespace

from ckanext.dcat.profiles import RDFProfile

DCAT = Namespace("http://www.w3.org/ns/dcat#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
DATASET = URIRef("http://example.org/dataset")


def _urls(contact):
    profile = RDFProfile(Graph())
    profile._add_contact_to_graph(DATASET, DCAT.contactPoint, contact)
    (contact_ref,) = profile.g.objects(DATASET, DCAT.contactPoint)
    return sorted(profile.g.objects(contact_ref, VCARD.hasURL))


def test_a_list_gives_one_iri_per_url():
    assert _urls({"name": "Support", "url": ["https://example.org/a", "https://example.org/b"]}) == [
        URIRef("https://example.org/a"),
        URIRef("https://example.org/b"),
    ]


def test_a_list_of_one_is_not_written_as_an_iri_holding_the_list():
    (url,) = _urls({"name": "Support", "url": ["https://example.org/support"]})

    assert url == URIRef("https://example.org/support")
    assert "[" not in str(url)


def test_a_string_is_one_iri_and_is_not_split_on_commas():
    # CleanedURIRef percent-encodes the comma; it is still one value
    assert _urls({"name": "Support", "url": "https://example.org/a,b"}) == [URIRef("https://example.org/a%2Cb")]


@pytest.mark.parametrize("url", [None, "", [], [""]])
def test_an_empty_url_writes_nothing(url):
    assert _urls({"name": "Support", "url": url}) == []


def test_spaces_in_a_url_are_still_cleaned():
    assert _urls({"name": "Support", "url": ["https://example.org/a b"]}) == [URIRef("https://example.org/a%20b")]
