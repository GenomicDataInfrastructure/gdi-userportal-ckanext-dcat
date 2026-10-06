from rdflib import PROV, Graph, URIRef, Literal
from rdflib.namespace import Namespace

from ckanext.dcat.profiles import RDFProfile

DCT = Namespace("http://purl.org/dc/terms/")
DATASET = URIRef("http://example.org/dataset")
NLD = "http://publications.europa.eu/resource/authority/country/NLD"
DEU = "http://publications.europa.eu/resource/authority/country/DEU"
DEU_BER = "http://publications.europa.eu/resource/authority/place/DEU_BER"
OTHER_COUNTRY = "http://www.wikidata.org/entity/Q183"
ROR = "https://ror.org/05wg1m734"
ORCID = "https://orcid.org/0000-0001-2345-6789"

AGENT_TTL = """
@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

<http://example.org/dataset> dct:publisher <http://example.org/org> .
<http://example.org/org> a foaf:Organization ;
    foaf:name "Org" ;
    dct:identifier <%(ror)s> , <%(orcid)s> ;
    dct:spatial <%(nld)s> , <%(deu)s> .
""" % {"ror": ROR, "orcid": ORCID, "nld": NLD, "deu": DEU}


def _serialised(agent_dict):
    profile = RDFProfile(Graph())
    profile._add_agent_to_graph(DATASET, DCT.publisher, agent_dict)
    agent = next(profile.g.objects(DATASET, DCT.publisher))
    return profile, agent


def _objects(profile, agent, predicate):
    return sorted(str(o) for o in profile.g.objects(agent, predicate))


class TestAgentDetailsMultiValue:

    def test_multiple_countries_and_identifiers_are_parsed_as_lists(self):
        g = Graph()
        g.parse(format="turtle", data=AGENT_TTL)

        publisher = RDFProfile(g)._agents_details(DATASET, DCT.publisher)[0]

        assert sorted(publisher["country"]) == sorted([NLD, DEU])
        assert sorted(publisher["identifier"]) == sorted([ROR, ORCID])

    def test_agent_without_country_and_identifier_gets_empty_lists(self):
        g = Graph()
        g.parse(
            format="turtle",
            data="""
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix foaf: <http://xmlns.com/foaf/0.1/> .
            <http://example.org/dataset> dct:publisher <http://example.org/org> .
            <http://example.org/org> a foaf:Organization ; foaf:name "Org" .
            """,
        )

        publisher = RDFProfile(g)._agents_details(DATASET, DCT.publisher)[0]

        assert publisher["country"] == []
        assert publisher["identifier"] == []


    def test_places_are_kept_as_harvested(self):
        g = Graph()
        g.parse(
            format="turtle",
            data="""
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix foaf: <http://xmlns.com/foaf/0.1/> .
            <http://example.org/dataset> dct:publisher <http://example.org/org> .
            <http://example.org/org> a foaf:Organization ; foaf:name "Org" ;
                dct:spatial <%(deu)s> , <%(ber)s> .
            """ % {"deu": DEU, "ber": DEU_BER},
        )

        publisher = RDFProfile(g)._agents_details(DATASET, DCT.publisher)[0]

        assert sorted(publisher["country"]) == sorted([DEU, DEU_BER])

    def test_non_eu_spatial_values_are_kept_as_harvested(self):
        g = Graph()
        g.parse(
            format="turtle",
            data="""
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix foaf: <http://xmlns.com/foaf/0.1/> .
            <http://example.org/dataset> dct:publisher <http://example.org/org> .
            <http://example.org/org> a foaf:Organization ; foaf:name "Org" ;
                dct:spatial <%(other)s> .
            """ % {"other": OTHER_COUNTRY},
        )

        publisher = RDFProfile(g)._agents_details(DATASET, DCT.publisher)[0]

        assert publisher["country"] == [OTHER_COUNTRY]

    def test_qualified_attribution_agent_parses_like_a_publisher(self):
        g = Graph()
        g.parse(
            format="turtle",
            data="""
            @prefix dct: <http://purl.org/dc/terms/> .
            @prefix foaf: <http://xmlns.com/foaf/0.1/> .
            @prefix prov: <http://www.w3.org/ns/prov#> .
            <http://example.org/dataset> prov:qualifiedAttribution <http://example.org/attr> .
            <http://example.org/attr> a prov:Attribution ;
                prov:agent [ a foaf:Agent ; foaf:name "Org" ;
                    dct:identifier "%(ror)s" , "%(orcid)s" ;
                    dct:spatial <%(nld)s> , <%(deu)s> , <%(ber)s> ] .
            """ % {"ror": ROR, "orcid": ORCID, "nld": NLD, "deu": DEU, "ber": DEU_BER},
        )

        agent = RDFProfile(g)._agents_details(
            URIRef("http://example.org/attr"), PROV.agent
        )[0]

        assert sorted(agent["country"]) == sorted([NLD, DEU, DEU_BER])
        assert sorted(agent["identifier"]) == sorted([ROR, ORCID])


class TestAddAgentToGraphMultiValue:

    def test_list_values_become_one_triple_each(self):
        profile, agent = _serialised(
            {"name": "Org", "country": [NLD, DEU], "identifier": [ROR, ORCID]}
        )

        assert _objects(profile, agent, DCT.spatial) == sorted([NLD, DEU])
        assert _objects(profile, agent, DCT.identifier) == sorted([ROR, ORCID])

    def test_legacy_scalar_values_become_a_single_triple(self):
        profile, agent = _serialised({"name": "Org", "country": NLD, "identifier": ROR})

        assert _objects(profile, agent, DCT.spatial) == [NLD]
        assert _objects(profile, agent, DCT.identifier) == [ROR]

    def test_empty_values_add_no_triples(self):
        profile, agent = _serialised(
            {"name": "Org", "country": [], "identifier": ["", None]}
        )

        assert _objects(profile, agent, DCT.spatial) == []
        assert _objects(profile, agent, DCT.identifier) == []

    def test_countries_are_uri_references_and_identifiers_are_literals(self):
        profile, agent = _serialised(
            {"name": "Org", "country": [NLD], "identifier": [ROR]}
        )

        assert (agent, DCT.spatial, URIRef(NLD)) in profile.g
        assert (agent, DCT.identifier, Literal(ROR)) in profile.g

    def test_parse_then_serialise_round_trip_keeps_every_value(self):
        g = Graph()
        g.parse(format="turtle", data=AGENT_TTL)
        parsed = RDFProfile(g)._agents_details(DATASET, DCT.publisher)[0]

        profile, agent = _serialised(parsed)
        reparsed = RDFProfile(profile.g)._agents_details(DATASET, DCT.publisher)[0]

        assert sorted(reparsed["country"]) == sorted([NLD, DEU])
        assert sorted(reparsed["identifier"]) == sorted([ROR, ORCID])
