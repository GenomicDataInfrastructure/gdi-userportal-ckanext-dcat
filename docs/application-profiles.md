# Application profiles

Besides the [base profiles](profiles.md) there are other profiles included to support other domain
specific application profiles.

!!! Note
    If you are interested in contributing a profile that might be useful for the wider community
    check the documentation on [writing custom profiles](writing-profiles.md) and the 
    [contribution guidelines](contributing.md#including-new-profiles).

## DCAT-AP-NL

### Introduction

This extension contains a profile (`euro_dcat_ap_nl`) implementing the properties that
[DCAT-AP-NL 3.0](https://docs.geostandaarden.nl/dcat/dcat-ap-nl30/), the Dutch national extension
of DCAT-AP 3, adds on top of core DCAT-AP 3.0.

DCAT-AP-NL mostly tightens cardinality and usage guidance on properties that already exist in
core DCAT-AP (e.g. restricting `dct:accessRights` to three specific values); those are not
reimplemented here, as they are already handled by the base DCAT-AP profiles. This profile only
implements properties that DCAT-AP-NL adds with no equivalent in core DCAT-AP, such as
`adms:status` on `dcat:Dataset`.

### Usage

`euro_dcat_ap_nl` is a standalone profile, not baked into any other profile's class
hierarchy — enable it by listing it alongside whichever other profile(s) your deployment
already uses, so both run in sequence over the same RDF graph/dataset dict. List it last so
its properties aren't overwritten by a profile that runs after it:

```ini
ckanext.dcat.rdf.profiles = fairdatapoint_dcat_ap euro_dcat_ap_nl
```

or on its own:

```ini
ckanext.dcat.rdf.profiles = euro_dcat_ap_nl
```

The DCAT-AP-NL profile is an extension of the RDF profile.

For the FAIRDataPoint harvester, the global `ckanext.dcat.rdf.profiles` setting is not
consulted — each harvest source's own `"profile"` config value is used instead. That value
also accepts a space-separated list of profile names, e.g.
`"profile": "fairdatapoint_dcat_ap euro_dcat_ap_nl"`, to opt a given harvest source into
DCAT-AP-NL properties.

### Field Mapping

For a full overview of how CKAN dataset fields map to DCAT-AP-NL properties, refer to the
[mapping table](mapping-nl.md#mapping-between-ckan-fields-and-dcat-ap-nl).

## HealthDCAT-AP

### Introduction

This extension contains a profile (`euro_health_dcat_ap`) for the
[HealthDCAT-AP](https://healthdcat-ap.github.io/) specification.
This is a health-related extension of the DCAT application profile for sharing information about
Catalogues containing Datasets and Data Services descriptions in Europe (DCAT-AP).

The development of a Health DCAT application profile aims to standardize health metadata within 
the scope of the [European Health Data Space](https://health.ec.europa.eu/ehealth-digital-health-and-care/european-health-data-space_en)
(EHDS), fostering greater interoperability, findability and accessibility of electronic health 
data across the EU.

The goal of this profile is to provide the wider FAIR community and other EU portals with a starting
point for implementing HealthDCAT-AP within their own data catalogs.

!!! Note
    HealthDCAT-AP is a draft specification: cardinalities, vocabularies and the namespace change
    between releases. The profile follows the HealthDCAT-AP model described above; the profile for
    Release 8 is `euro_health_dcat_ap_r8`, see [Release 8](#release-8).


### Usage

Use the included `euro_health_dcat_ap` profile in your configuration:

```ini
ckanext.dcat.rdf.profiles = euro_health_dcat_ap
```

The HealthDCAT-AP profile is an extension of the DCAT-AP v3 profile and requires ckanext-scheming.
See the [documentation](getting-started.md#schemas) on how to set it up. You can use the included
`health_dcat_ap.yaml` schema file as a starting point to adapt it to your needs:

```ini
scheming.dataset_schemas = ckanext.dcat.schemas:health_dcat_ap.yaml
```

The profile has no settings of its own.


### Release 8

`euro_health_dcat_ap_r8` implements HealthDCAT-AP Release 8 on top of `euro_health_dcat_ap`. It is
enabled by listing it in place of `euro_health_dcat_ap`. The field mapping is in
[mapping-healthdcat.md](mapping-healthdcat.md); the open differences from the specification are in
the [Release 8 note](healthdcat-ap-r8-gap-analysis.md).

### Field Mapping

For a full overview of how CKAN dataset fields map to HealthDCAT-AP properties (including DPV fields), refer to the [mapping table](mapping-healthdcat.md#mapping-between-ckan-fields-and-healthdcat-ap). This table documents the semantic relationship between CKAN schema fields and RDF predicates used in the `euro_health_dcat_ap` profile implementation.


### Limitations and deviations

As HealthDCAT-AP is still a draft, it is bound to change. There are currently still some
inconsistencies in the standard and unclarities regarding certain properties. Below is a short summary
of limitations and implementaiton decisions made during development of this profile.

1. Cardinalities have not yet been finalized for HealthDCAT-AP. This CKAN schema has taken a very
   liberal approach and takes all values as strictly optional (no failed validation for missing
   fields). Note that some mandatory fields are currently impossible to fill with real data e.g. the
   Health Data Access Body (HDAB) field: the EHDS legislation has not been implemented yet and no HDABs
   have been formally appointed.
2. The profile uses the namespace `http://healthdataportal.eu/ns/health#`. Changing the namespace
   means changing the profile.
3. The official examples of the standard uses the `dct:description` property to encode the data
   purpose. This does not seem to be according to the Data Privacy Vocabulary specification, which
   proposes a controlled vocabulary. See [this issue](https://github.com/HealthDCAT-AP-de/healthdcat-ap.de/issues/11) 
   for the German perspective on this.
4. *analytics* is read and written as a list of IRIs; the resources behind them are not loaded.
   *sample* is an upstream DCAT-AP 3 property and is read by that profile.
5. Documentation (*foaf:page*) is implemented as an URI. There is some HealthDCAT-AP example data
  out in the wild that uses a blank node for this and adds several properties, however this is
   inconsistent with other DCAT implementations.
6. Dataset series follow the DCAT-AP 3 profile, which this profile extends. The health-specific
   fields are not defined on a series.
7. The *quality annotation* is read and written as a `dqv:hasQualityAnnotation` with an
   `oa:Annotation`. Only annotations whose body and target are `http(s)` IRIs are kept.
8. Language-tagged values are supported for the fields listed in `MULTILINGUAL_LITERAL_FIELDS` of
   the profile, and need a multilingual schema; see [Multilingual support](profiles.md#multilingual-support).
9. For other properties, any limitations from the DCAT-AP profiles still apply.
