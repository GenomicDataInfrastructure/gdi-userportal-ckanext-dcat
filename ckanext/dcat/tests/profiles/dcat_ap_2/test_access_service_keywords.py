import json

from rdflib import Graph, URIRef
from rdflib.namespace import Namespace

from ckanext.dcat.profiles.euro_dcat_ap_2 import EuropeanDCATAP2Profile

DCAT = Namespace("http://www.w3.org/ns/dcat#")
DATASET = URIRef("http://example.org/d")

PREFIXES = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
"""


def _parse_access_service(keyword_triples):
    ttl = PREFIXES + """
    <http://example.org/d> a dcat:Dataset ; dct:title "T" ;
        dcat:distribution <http://example.org/dist> .
    <http://example.org/dist> a dcat:Distribution ;
        dcat:accessService <http://example.org/svc> .
    <http://example.org/svc> a dcat:DataService ; dct:title "S" ;
        dcat:endpointURL <http://example.org/ep> %s .
    """ % keyword_triples
    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    dataset_dict = {"resources": []}

    EuropeanDCATAP2Profile(graph).parse_dataset(dataset_dict, DATASET)

    return json.loads(dataset_dict["resources"][0]["access_services"])[0]


def _serialised_keywords(access_service):
    graph = Graph()
    dataset_dict = {
        "id": "d1",
        "name": "t",
        "title": "T",
        "resources": [
            {
                "id": "r1",
                "name": "R",
                "uri": "http://example.org/dist",
                "access_services": json.dumps([access_service]),
            }
        ],
    }

    EuropeanDCATAP2Profile(graph).graph_from_dataset(dataset_dict, DATASET)

    return sorted((str(o), o.language) for o in graph.objects(None, DCAT.keyword))


class TestParseAccessServiceKeywords:

    def test_keywords_are_grouped_by_language(self):
        service = _parse_access_service(';\n dcat:keyword "genomics"@en , "genomica"@nl')

        assert service["keyword_translated"]["en"] == ["genomics"]
        assert service["keyword_translated"]["nl"] == ["genomica"]

    def test_untagged_keywords_use_the_default_language(self):
        service = _parse_access_service(';\n dcat:keyword "plain"')

        assert "plain" in service["keyword_translated"]["en"]

    def test_plain_keyword_list_keeps_every_language_for_older_readers(self):
        service = _parse_access_service(';\n dcat:keyword "genomics"@en , "genomica"@nl')

        assert sorted(service["keyword"]) == ["genomica", "genomics"]

    def test_no_keywords_stores_neither_field(self):
        service = _parse_access_service("")

        assert "keyword_translated" not in service
        assert "keyword" not in service


class TestSerialiseAccessServiceKeywords:
    ENDPOINT = {"title": "S", "endpoint_url": ["http://example.org/ep"]}

    def test_translated_keywords_are_written_with_their_language(self):
        keywords = _serialised_keywords(
            dict(
                self.ENDPOINT,
                keyword_translated={"en": ["genomics"], "nl": ["genomica"]},
                keyword=["genomics", "genomica"],
            )
        )

        assert keywords == [("genomica", "nl"), ("genomics", "en")]

    def test_legacy_keywords_are_written_without_language(self):
        keywords = _serialised_keywords(dict(self.ENDPOINT, keyword=["one", "two"]))

        assert keywords == [("one", None), ("two", None)]

    def test_all_empty_translations_fall_back_to_the_legacy_keywords(self):
        keywords = _serialised_keywords(
            dict(
                self.ENDPOINT,
                keyword_translated={"en": [], "nl": []},
                keyword=["legacy"],
            )
        )

        assert keywords == [("legacy", None)]

    def test_blank_translated_keywords_are_skipped(self):
        keywords = _serialised_keywords(
            dict(self.ENDPOINT, keyword_translated={"en": ["genomics", ""], "nl": []})
        )

        assert keywords == [("genomics", "en")]
