"""
Metadata profiles of a deployment, and the one a harvest source selects.

A deployment enables one or more metadata profiles (for example ``gdi_current`` and
``healthdcat_r8``) and names one of them the main profile. ``gdi_userportal``'s profile
pack generator writes that to the CKAN config at container start::

    ckanext.dcat.metadata_profiles = healthdcat_r8 gdi_current
    ckanext.dcat.metadata_profiles.main = gdi_current
    ckanext.dcat.metadata_profiles.<name>.rdf_profiles = <ckan.rdf.profiles entry points>

A harvest source picks its profile with the ``metadata_profile`` key of its config JSON.
Empty or absent means the main profile. The older ``profile`` key (a space-separated chain
of raw RDF profile names) stays as an explicit override; setting both is an error.

This module reads plain mappings and imports no CKAN code.
"""
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, List, Mapping, Optional, Set

METADATA_PROFILES_OPTION = "ckanext.dcat.metadata_profiles"
MAIN_PROFILE_OPTION = "ckanext.dcat.metadata_profiles.main"
PACK_RDF_PROFILES_OPTION = "ckanext.dcat.metadata_profiles.{name}.rdf_profiles"
# The deployment-wide default chain every code path without a source already reads.
RDF_PROFILES_OPTION = "ckanext.dcat.rdf.profiles"
RDF_PROFILES_ENTRY_POINT_GROUP = "ckan.rdf.profiles"

SOURCE_METADATA_PROFILE_KEY = "metadata_profile"
SOURCE_RDF_PROFILE_KEY = "profile"

ORIGIN_METADATA_PROFILE = SOURCE_METADATA_PROFILE_KEY
ORIGIN_RDF_PROFILE = SOURCE_RDF_PROFILE_KEY
ORIGIN_DEFAULT = "default"


class MetadataProfileError(ValueError):
    """The metadata profile a source asks for cannot be used. The message is meant for the user."""


@dataclass(frozen=True)
class ResolvedProfile:
    """The profile a harvest source effectively uses.

    ``name`` is None when the chain comes from the legacy ``profile`` key or from a deployment
    without metadata profiles. ``origin`` says which of the three ways produced it.
    """

    name: Optional[str]
    rdf_profiles: List[str]
    origin: str

    def describe(self) -> str:
        label = f"metadata profile '{self.name}'" if self.name else "no named metadata profile"
        chain = " ".join(self.rdf_profiles) or "(parser default)"
        return f"{label}, RDF profiles: {chain}, from: {self.origin}"


def _names(value: Any) -> List[str]:
    """A config value as a list of names: a list as is, a string split on whitespace and commas."""
    if value is None:
        return []
    if isinstance(value, str):
        return value.replace(",", " ").split()
    return [str(item).strip() for item in value if str(item).strip()]


def enabled_profiles(config: Mapping) -> List[str]:
    """The metadata profiles the deployment enables, in precedence order. Empty when none are configured."""
    return _names(config.get(METADATA_PROFILES_OPTION))


def main_profile(config: Mapping) -> Optional[str]:
    """The profile used when a source names none: the configured main, else the first enabled."""
    enabled = enabled_profiles(config)
    if not enabled:
        return None
    main = (config.get(MAIN_PROFILE_OPTION) or "").strip()
    if not main:
        return enabled[0]
    if main not in enabled:
        raise MetadataProfileError(
            f"The main metadata profile '{main}' is not enabled on this deployment. "
            f"Enabled: {', '.join(enabled)}"
        )
    return main


def rdf_profiles_of(config: Mapping, name: str) -> List[str]:
    """The ordered ``ckan.rdf.profiles`` entry points of an enabled metadata profile."""
    chain = _names(config.get(PACK_RDF_PROFILES_OPTION.format(name=name)))
    if not chain:
        raise MetadataProfileError(
            f"No RDF profiles are configured for metadata profile '{name}' "
            f"({PACK_RDF_PROFILES_OPTION.format(name=name)})"
        )
    return chain


def installed_rdf_profiles() -> Set[str]:
    return {entry_point.name for entry_point in entry_points(group=RDF_PROFILES_ENTRY_POINT_GROUP)}


def _text(source_config: Mapping, key: str) -> Optional[str]:
    """A string option of a source config; None when absent, null or blank."""
    value = source_config.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MetadataProfileError(
            f"'{key}' must be a string, got {type(value).__name__}: {value!r}"
        )
    return value.strip() or None


def resolve_source_profile(
    source_config: Mapping,
    config: Mapping,
    installed: Optional[Set[str]] = None,
) -> ResolvedProfile:
    """
    The profile a harvest source uses, from its config JSON (already a dict) and the CKAN config.

    ``installed`` is the set of installed RDF profile names. When given, the legacy ``profile``
    key is checked against it; leave it out at run time, where the parser reports an unknown
    name itself.

    Raises MetadataProfileError, with a message naming the enabled profiles where that helps.
    """
    metadata_profile = _text(source_config, SOURCE_METADATA_PROFILE_KEY)
    rdf_profile = _text(source_config, SOURCE_RDF_PROFILE_KEY)

    if metadata_profile and rdf_profile:
        raise MetadataProfileError(
            f"Both '{SOURCE_METADATA_PROFILE_KEY}' and '{SOURCE_RDF_PROFILE_KEY}' are set, "
            f"which is ambiguous. Use '{SOURCE_METADATA_PROFILE_KEY}' to pick a metadata profile, "
            f"or '{SOURCE_RDF_PROFILE_KEY}' to give a raw RDF profile chain, not both."
        )

    if rdf_profile:
        chain = rdf_profile.split()
        if installed is not None:
            missing = [name for name in chain if name not in installed]
            if missing:
                raise MetadataProfileError(
                    f"'{SOURCE_RDF_PROFILE_KEY}' names RDF profiles that are not installed: "
                    f"{', '.join(missing)}. Installed: {', '.join(sorted(installed))}"
                )
        return ResolvedProfile(None, chain, ORIGIN_RDF_PROFILE)

    enabled = enabled_profiles(config)

    if metadata_profile:
        if metadata_profile not in enabled:
            listed = ", ".join(enabled) if enabled else "(none configured)"
            raise MetadataProfileError(
                f"Metadata profile '{metadata_profile}' is not enabled on this deployment. "
                f"Enabled: {listed}"
            )
        return ResolvedProfile(
            metadata_profile, rdf_profiles_of(config, metadata_profile), ORIGIN_METADATA_PROFILE
        )

    main = main_profile(config)
    if main:
        return ResolvedProfile(main, rdf_profiles_of(config, main), ORIGIN_DEFAULT)

    # A deployment that never ran the profile generator: the chain every other path uses.
    return ResolvedProfile(None, _names(config.get(RDF_PROFILES_OPTION)), ORIGIN_DEFAULT)
