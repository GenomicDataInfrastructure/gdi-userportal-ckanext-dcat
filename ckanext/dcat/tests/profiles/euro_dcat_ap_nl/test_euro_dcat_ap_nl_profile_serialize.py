import pytest
from rdflib.term import URIRef

from ckanext.dcat.processors import RDFSerializer
from ckanext.dcat.profiles import ADMS
from ckanext.dcat.tests.utils import BaseSerializeTest


@pytest.mark.usefixtures("with_plugins")
@pytest.mark.ckan_config("ckan.plugins", "dcat")
@pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "euro_dcat_ap_nl")
class TestEuroDCATAPNLProfileSerialize(BaseSerializeTest):
    def test_dataset_status(self):
        """
        dataset_status should serialize to adms:status on the dataset
        subject, the DCAT-AP-NL 3.0 addition (core DCAT-AP only defines
        adms:status for dcat:Distribution/CatalogRecord). Should serialize
        standalone, without HealthDCAT-AP loaded.
        """
        dataset_dict = {
            "id": "test-dataset-nl-status",
            "name": "test-dataset-nl-status",
            "title": "Test dataset",
            "notes": "A test dataset",
            "dataset_status": (
                "http://publications.europa.eu/resource/authority/dataset-status/DEVELOP"
            ),
        }

        s = RDFSerializer()
        g = s.g

        dataset_ref = s.graph_from_dataset(dataset_dict)

        statuses = [t for t in g.triples((dataset_ref, ADMS.status, None))]
        assert len(statuses) == 1
        assert statuses[0][2] == URIRef(dataset_dict["dataset_status"])
