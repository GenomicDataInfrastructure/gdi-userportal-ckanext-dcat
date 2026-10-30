"""
Which metadata profile a harvest source uses. Pure tests: plain dicts, no CKAN.
"""
import pytest

from ckanext.dcat.metadata_profiles import (
    ORIGIN_DEFAULT,
    ORIGIN_METADATA_PROFILE,
    ORIGIN_RDF_PROFILE,
    MetadataProfileError,
    enabled_profiles,
    main_profile,
    resolve_source_profile,
)

GDI_CHAIN = ["fairdatapoint_dcat_ap", "euro_dcat_ap_nl"]
R8_CHAIN = ["euro_health_dcat_ap_r8"]

BOTH = {
    "ckanext.dcat.metadata_profiles": "healthdcat_r8 gdi_current",
    "ckanext.dcat.metadata_profiles.main": "gdi_current",
    "ckanext.dcat.metadata_profiles.gdi_current.rdf_profiles": "fairdatapoint_dcat_ap euro_dcat_ap_nl",
    "ckanext.dcat.metadata_profiles.healthdcat_r8.rdf_profiles": "euro_health_dcat_ap_r8",
    "ckanext.dcat.rdf.profiles": "fairdatapoint_dcat_ap euro_dcat_ap_nl",
}

# What a deployment with only gdi_current enables. The ini keeps the key of the retired
# pack from an earlier start, which must not make it enabled.
ONLY_GDI = {
    "ckanext.dcat.metadata_profiles": "gdi_current",
    "ckanext.dcat.metadata_profiles.main": "gdi_current",
    "ckanext.dcat.metadata_profiles.gdi_current.rdf_profiles": "fairdatapoint_dcat_ap euro_dcat_ap_nl",
    "ckanext.dcat.metadata_profiles.healthdcat_r8.rdf_profiles": "euro_health_dcat_ap_r8",
    "ckanext.dcat.rdf.profiles": "fairdatapoint_dcat_ap euro_dcat_ap_nl",
}

INSTALLED = {"fairdatapoint_dcat_ap", "euro_dcat_ap_nl", "euro_health_dcat_ap_r8", "euro_dcat_ap_3"}


class TestNoProfileInTheSource:
    @pytest.mark.parametrize(
        "source_config",
        [
            {},
            {"metadata_profile": None},
            {"metadata_profile": ""},
            {"metadata_profile": "   "},
            {"request_timeout": 100},
        ],
        ids=["empty", "null", "empty string", "blank", "other keys only"],
    )
    def test_gets_the_main_profile(self, source_config):
        resolved = resolve_source_profile(source_config, BOTH)

        assert resolved.name == "gdi_current"
        assert resolved.rdf_profiles == GDI_CHAIN
        assert resolved.origin == ORIGIN_DEFAULT

    def test_follows_the_main_profile_of_the_deployment(self):
        config = {**BOTH, "ckanext.dcat.metadata_profiles.main": "healthdcat_r8"}

        resolved = resolve_source_profile({}, config)

        assert (resolved.name, resolved.rdf_profiles) == ("healthdcat_r8", R8_CHAIN)

    def test_main_defaults_to_the_first_enabled_profile(self):
        config = {k: v for k, v in BOTH.items() if k != "ckanext.dcat.metadata_profiles.main"}

        assert main_profile(config) == "healthdcat_r8"
        assert resolve_source_profile({}, config).name == "healthdcat_r8"

    def test_a_main_profile_that_is_not_enabled_is_a_configuration_error(self):
        config = {**BOTH, "ckanext.dcat.metadata_profiles.main": "gdi_legacy"}

        with pytest.raises(MetadataProfileError, match="main metadata profile 'gdi_legacy'.*Enabled: healthdcat_r8, gdi_current"):
            resolve_source_profile({}, config)


class TestMetadataProfileInTheSource:
    def test_selects_gdi_current(self):
        resolved = resolve_source_profile({"metadata_profile": "gdi_current"}, BOTH)

        assert (resolved.name, resolved.rdf_profiles, resolved.origin) == (
            "gdi_current",
            GDI_CHAIN,
            ORIGIN_METADATA_PROFILE,
        )

    def test_selects_a_profile_that_is_not_the_main_one(self):
        resolved = resolve_source_profile({"metadata_profile": "healthdcat_r8"}, BOTH)

        assert (resolved.name, resolved.rdf_profiles, resolved.origin) == (
            "healthdcat_r8",
            R8_CHAIN,
            ORIGIN_METADATA_PROFILE,
        )

    def test_ignores_whitespace_around_the_name(self):
        assert resolve_source_profile({"metadata_profile": " healthdcat_r8 "}, BOTH).name == "healthdcat_r8"

    def test_a_profile_that_is_not_enabled_is_rejected_naming_the_enabled_ones(self):
        with pytest.raises(MetadataProfileError) as error:
            resolve_source_profile({"metadata_profile": "healthdcat_r8"}, ONLY_GDI)

        assert str(error.value) == (
            "Metadata profile 'healthdcat_r8' is not enabled on this deployment. Enabled: gdi_current"
        )

    def test_an_unknown_name_is_rejected_the_same_way(self):
        with pytest.raises(MetadataProfileError) as error:
            resolve_source_profile({"metadata_profile": "healthdcat_r9"}, BOTH)

        assert "'healthdcat_r9' is not enabled" in str(error.value)
        assert "Enabled: healthdcat_r8, gdi_current" in str(error.value)

    def test_the_name_is_case_sensitive(self):
        with pytest.raises(MetadataProfileError, match="'GDI_current' is not enabled"):
            resolve_source_profile({"metadata_profile": "GDI_current"}, BOTH)

    @pytest.mark.parametrize("value", [123, True, ["gdi_current"], {"name": "gdi_current"}])
    def test_a_value_that_is_not_a_string_is_rejected(self, value):
        with pytest.raises(MetadataProfileError, match="'metadata_profile' must be a string"):
            resolve_source_profile({"metadata_profile": value}, BOTH)

    def test_an_enabled_profile_without_rdf_profiles_is_a_configuration_error(self):
        config = {k: v for k, v in BOTH.items() if "healthdcat_r8.rdf_profiles" not in k}

        with pytest.raises(MetadataProfileError, match="No RDF profiles are configured for metadata profile 'healthdcat_r8'"):
            resolve_source_profile({"metadata_profile": "healthdcat_r8"}, config)


class TestLegacyProfileKey:
    def test_a_raw_chain_is_used_as_given(self):
        resolved = resolve_source_profile({"profile": "fairdatapoint_dcat_ap"}, BOTH)

        assert (resolved.name, resolved.rdf_profiles, resolved.origin) == (
            None,
            ["fairdatapoint_dcat_ap"],
            ORIGIN_RDF_PROFILE,
        )

    def test_a_chain_of_several_profiles(self):
        resolved = resolve_source_profile({"profile": "fairdatapoint_dcat_ap euro_dcat_ap_nl"}, BOTH)

        assert resolved.rdf_profiles == GDI_CHAIN

    def test_an_empty_profile_means_the_main_profile(self):
        assert resolve_source_profile({"profile": ""}, BOTH).origin == ORIGIN_DEFAULT

    def test_both_keys_are_ambiguous(self):
        with pytest.raises(MetadataProfileError, match="Both 'metadata_profile' and 'profile' are set"):
            resolve_source_profile({"metadata_profile": "gdi_current", "profile": "euro_dcat_ap_3"}, BOTH)

    def test_an_empty_metadata_profile_next_to_a_profile_is_not_ambiguous(self):
        resolved = resolve_source_profile({"metadata_profile": "", "profile": "euro_dcat_ap_3"}, BOTH)

        assert resolved.rdf_profiles == ["euro_dcat_ap_3"]

    def test_an_installed_profile_passes_the_check(self):
        resolved = resolve_source_profile({"profile": "euro_dcat_ap_3"}, BOTH, installed=INSTALLED)

        assert resolved.rdf_profiles == ["euro_dcat_ap_3"]

    def test_a_profile_that_is_not_installed_is_rejected_when_checked(self):
        with pytest.raises(MetadataProfileError, match="not installed: euro_dcat_ap_9"):
            resolve_source_profile({"profile": "euro_dcat_ap_3 euro_dcat_ap_9"}, BOTH, installed=INSTALLED)

    def test_it_is_not_checked_when_no_installed_set_is_given(self):
        assert resolve_source_profile({"profile": "euro_dcat_ap_9"}, BOTH).rdf_profiles == ["euro_dcat_ap_9"]

    def test_the_legacy_key_works_on_a_deployment_that_enables_only_one_profile(self):
        resolved = resolve_source_profile({"profile": "euro_health_dcat_ap_r8"}, ONLY_GDI)

        assert resolved.rdf_profiles == R8_CHAIN


class TestDeploymentWithoutMetadataProfiles:
    CONFIG = {"ckanext.dcat.rdf.profiles": "euro_dcat_ap_3 euro_dcat_ap_nl"}

    def test_a_source_without_a_profile_gets_the_default_chain(self):
        resolved = resolve_source_profile({}, self.CONFIG)

        assert (resolved.name, resolved.rdf_profiles, resolved.origin) == (
            None,
            ["euro_dcat_ap_3", "euro_dcat_ap_nl"],
            ORIGIN_DEFAULT,
        )

    def test_without_any_chain_the_result_is_empty_and_the_parser_default_applies(self):
        assert resolve_source_profile({}, {}).rdf_profiles == []

    def test_a_named_profile_is_rejected_and_says_none_are_configured(self):
        with pytest.raises(MetadataProfileError, match=r"Enabled: \(none configured\)"):
            resolve_source_profile({"metadata_profile": "gdi_current"}, self.CONFIG)


class TestConfigValues:
    def test_a_list_valued_option_is_read_like_a_string(self):
        config = {**BOTH, "ckanext.dcat.metadata_profiles": ["healthdcat_r8", "gdi_current"]}

        assert enabled_profiles(config) == ["healthdcat_r8", "gdi_current"]

    def test_commas_separate_like_spaces(self):
        config = {**BOTH, "ckanext.dcat.metadata_profiles": "healthdcat_r8, gdi_current"}

        assert enabled_profiles(config) == ["healthdcat_r8", "gdi_current"]

    def test_the_description_names_profile_and_chain(self):
        resolved = resolve_source_profile({"metadata_profile": "healthdcat_r8"}, BOTH)

        assert resolved.describe() == (
            "metadata profile 'healthdcat_r8', RDF profiles: euro_health_dcat_ap_r8, from: metadata_profile"
        )
