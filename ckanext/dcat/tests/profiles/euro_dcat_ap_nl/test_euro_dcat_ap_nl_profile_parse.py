import pytest

from ckanext.dcat.processors import RDFParser
from ckanext.dcat.tests.utils import BaseParseTest


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "dcat scheming_datasets")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.dcat.schemas:dcat_ap_full.yaml"
)
@pytest.mark.ckan_config(
    "scheming.presets",
    "ckanext.scheming:presets.json ckanext.dcat.schemas:presets.yaml",
)
@pytest.mark.ckan_config("ckanext.dcat.rdf.profiles", "euro_dcat_ap_nl")
class TestEuroDCATAPNLProfileParse(BaseParseTest):
    def test_dataset_status(self):
        """
        adms:status on the dataset subject is a DCAT-AP-NL 3.0 addition
        (core DCAT-AP only defines it for dcat:Distribution/CatalogRecord).
        Should parse standalone, without HealthDCAT-AP loaded.
        """
        data = """
        @prefix dcat: <http://www.w3.org/ns/dcat#> .
        @prefix dct: <http://purl.org/dc/terms/> .
        @prefix adms: <http://www.w3.org/ns/adms#> .

        <https://example.com/dataset1>
          a dcat:Dataset ;
          dct:title "Test dataset" ;
          dct:description "A test dataset" ;
          adms:status <http://publications.europa.eu/resource/authority/dataset-status/DEVELOP> ;
        .
        """

        p = RDFParser()
        p.parse(data, _format="ttl")
        datasets = [d for d in p.datasets()]

        assert len(datasets) == 1
        assert datasets[0]["dataset_status"] == (
            "http://publications.europa.eu/resource/authority/dataset-status/DEVELOP"
        )
