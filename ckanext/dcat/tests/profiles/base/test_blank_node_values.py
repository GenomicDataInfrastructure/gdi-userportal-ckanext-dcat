"""
A blank node that is read as a plain value used to become its internal id
("n1b2c3...b7"). It stands for its text instead, and for nothing if it has none.
"""
from unittest import mock

from rdflib import RDFS, Graph, Literal, URIRef

from ckanext.dcat.profiles import RDFProfile

DATASET = URIRef("http://example.org/dataset")
DCT = "http://purl.org/dc/terms/"

PREFIXES = """
@prefix dct: <http://purl.org/dc/terms/> .
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix adms: <http://www.w3.org/ns/adms#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
"""


def _profile(body):
    g = Graph().parse(data=PREFIXES + "<http://example.org/dataset> a dcat:Dataset ; " + body, format="turtle")
    return RDFProfile(g)


def _values(body):
    return sorted(_profile(body)._object_value_list(DATASET, URIRef(DCT + "relation")))


def test_an_iri_and_a_literal_are_read_as_before():
    assert _values('dct:relation <http://example.org/a>, "text" .') == ["http://example.org/a", "text"]


def test_a_blank_node_gives_its_description():
    assert _values('dct:relation [ dct:description "Consent under the EHDS" ] .') == ["Consent under the EHDS"]


def test_a_blank_node_gives_its_notation():
    assert _values('dct:relation [ a adms:Identifier ; skos:notation "ONC-EHR-2024" ] .') == ["ONC-EHR-2024"]


def test_a_blank_node_prefers_its_label_over_its_description():
    assert _values('dct:relation [ rdfs:label "Label" ; dct:description "Description" ] .') == ["Label"]


def test_a_blank_node_without_text_gives_nothing_instead_of_its_id():
    assert _values("dct:relation [ a dct:Standard ] .") == []


def test_the_text_of_a_blank_node_is_taken_in_the_default_language():
    profile = _profile('dct:relation [ rdfs:label "Etikett"@de , "Label"@en ] .')
    profile._default_lang = "en"

    assert profile._object_value_list(DATASET, URIRef(DCT + "relation")) == ["Label"]


def _text_of_a_node_whose_graph_lists(labels):
    """The text of a blank node, when the graph hands out its rdfs:label literals in the given order."""
    profile = _profile("dct:relation [ a dct:Standard ] .")
    node = next(iter(profile.g.objects(DATASET, URIRef(DCT + "relation"))))

    def objects(subject, predicate, *args, **kwargs):
        return iter(labels if predicate == RDFS.label else [])

    with mock.patch.object(profile.g, "objects", objects):
        profile._default_lang = "en"
        return profile._blank_node_text(node)


def test_the_text_of_a_blank_node_does_not_depend_on_the_order_of_the_graph():
    labels = [Literal("Etikett", lang="de"), Literal("Label", lang="fr"), Literal("Etichetta", lang="it")]

    assert _text_of_a_node_whose_graph_lists(labels) == _text_of_a_node_whose_graph_lists(labels[::-1])


def test_the_default_language_text_does_not_depend_on_the_order_of_the_graph():
    labels = [Literal("B", lang="en"), Literal("A", lang="en"), Literal("Etikett", lang="de")]

    assert _text_of_a_node_whose_graph_lists(labels) == _text_of_a_node_whose_graph_lists(labels[::-1]) == "A"


def test_a_blank_node_next_to_an_iri_keeps_the_iri():
    assert _values('dct:relation <http://example.org/a>, [ rdfs:label "Label" ], [ a dct:Standard ] .') == [
        "Label",
        "http://example.org/a",
    ]


def test_a_single_value_read_gives_the_text_of_a_blank_node():
    profile = _profile('dct:type [ dct:description "Statistical data" ] .')

    assert profile._object_value(DATASET, URIRef(DCT + "type")) == "Statistical data"


def test_a_single_value_read_never_gives_the_id_of_a_blank_node():
    profile = _profile("dct:type [ a dct:Standard ] .")

    assert profile._object_value(DATASET, URIRef(DCT + "type")) == ""


def test_a_single_value_read_skips_a_blank_node_without_text_for_the_next_value():
    profile = _profile('dct:type [ a dct:Standard ] , <http://example.org/type> .')

    assert profile._object_value(DATASET, URIRef(DCT + "type")) == "http://example.org/type"
