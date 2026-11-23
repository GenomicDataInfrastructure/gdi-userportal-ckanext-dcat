"""
The RDF harvester parses a source with the RDF profile chain of the metadata profile that the source names
(``metadata_profile``), or the one of the deployment's main profile. A profile that is not enabled fails the
job with a gather error: there is no silent fallback. Without a CKAN database.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from ckanext.dcat.harvesters.rdf import DCATRDFHarvester

CONFIG = {
    "ckanext.dcat.metadata_profiles": "healthdcat_r8 gdi_current",
    "ckanext.dcat.metadata_profiles.main": "gdi_current",
    "ckanext.dcat.metadata_profiles.healthdcat_r8.rdf_profiles": "euro_health_dcat_ap_r8",
    "ckanext.dcat.metadata_profiles.gdi_current.rdf_profiles": "fairdatapoint_dcat_ap euro_dcat_ap_nl",
}


@pytest.fixture
def harvester():
    instance = DCATRDFHarvester()
    instance._save_gather_error = MagicMock()
    return instance


@pytest.fixture(autouse=True)
def deployment_config():
    with patch("ckanext.dcat.harvesters.rdf.p.toolkit.config", CONFIG):
        yield


def _job(source_config):
    job = MagicMock()
    job.source.id = "source-id"
    job.source.config = json.dumps(source_config) if source_config is not None else None
    return job


def test_a_source_without_a_profile_is_parsed_with_the_main_profile(harvester):
    assert harvester._source_rdf_profiles(_job(None)) == ["fairdatapoint_dcat_ap", "euro_dcat_ap_nl"]
    assert harvester._source_rdf_profiles(_job({"rdf_format": "text/turtle"})) == [
        "fairdatapoint_dcat_ap",
        "euro_dcat_ap_nl",
    ]


def test_a_source_with_a_metadata_profile_is_parsed_with_its_chain(harvester):
    chain = harvester._source_rdf_profiles(_job({"metadata_profile": "healthdcat_r8"}))

    assert chain == ["euro_health_dcat_ap_r8"]


def test_a_profile_that_is_not_enabled_is_an_error_and_not_a_fallback(harvester):
    from ckanext.dcat.metadata_profiles import MetadataProfileError

    with pytest.raises(MetadataProfileError, match="not enabled"):
        harvester._source_rdf_profiles(_job({"metadata_profile": "retired_profile"}))


def test_the_gather_of_such_a_source_reports_the_error_and_harvests_nothing(harvester):
    job = _job({"metadata_profile": "retired_profile"})

    assert harvester.gather_stage(job) == []

    message, saved_for = harvester._save_gather_error.call_args[0]
    assert "source-id" in message and "retired_profile" in message and saved_for is job


def test_a_source_config_that_names_both_keys_is_rejected_when_it_is_saved(harvester):
    with pytest.raises(ValueError, match="ambiguous"):
        harvester.validate_config(json.dumps({"metadata_profile": "healthdcat_r8", "profile": "euro_dcat_ap_3"}))


def test_a_source_config_with_an_enabled_profile_is_accepted(harvester):
    config = json.dumps({"metadata_profile": "healthdcat_r8"})

    assert harvester.validate_config(config) == config


def test_a_source_config_with_a_profile_that_is_not_enabled_is_rejected(harvester):
    with pytest.raises(ValueError, match="not enabled"):
        harvester.validate_config(json.dumps({"metadata_profile": "retired_profile"}))
