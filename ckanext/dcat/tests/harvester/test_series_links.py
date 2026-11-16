"""
A harvested dataset is linked to the series it points at with dcat:inSeries, when that series is part of
the same harvest source: the mapping the harvester builds holds only the series of that source. A
reference to anything else (an unknown URI, a blank node, a literal) is skipped and the dataset is
imported without that link. Without a CKAN database.
"""
from rdflib import Graph

from ckanext.dcat.processors import RDFParser

IN_SOURCE = "http://example.org/series-in-source"
ELSEWHERE = "http://example.org/series-of-another-source"
UNKNOWN = "http://example.org/fake_series"

TURTLE = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://example.org/dataset> a dcat:Dataset ;
    dct:title "Test dataset" ;
    dcat:inSeries <%s>, <%s>, <%s>, [ a dcat:DatasetSeries ], "not a uri" .
""" % (IN_SOURCE, ELSEWHERE, UNKNOWN)


def _dataset(series_mapping):
    parser = RDFParser(profiles=["euro_dcat_ap_3"])
    parser.g = Graph()
    parser.g.parse(data=TURTLE, format="turtle")
    (dataset,) = list(parser.datasets(series_mapping))
    return dataset


def test_the_dataset_is_linked_to_the_series_of_its_source_only():
    dataset = _dataset({IN_SOURCE: {"id": "id-in-source", "name": "in-source"}})

    assert dataset["in_series"] == ["id-in-source"]


def test_a_dataset_that_points_at_no_known_series_gets_no_in_series():
    assert "in_series" not in _dataset({})
    assert "in_series" not in _dataset(None)
