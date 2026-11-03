## Mapping between CKAN fields and HealthDCAT-AP

This page lists how the health-specific CKAN dataset fields map to the
[HealthDCAT-AP](https://data.health.europa.eu/healthdcat-ap/) properties (namespace
`healthdcatap:` = `http://healthdataportal.eu/ns/health#`, plus `dpv:`, `dqv:`, `oa:` and, for R8,
`cv:`, `csvw:`, `time:` and `geodcatap:`). The plain DCAT-AP fields are in [mapping.md](mapping.md).

**The CKAN field names are the same in every profile.** A profile decides only how a field is read
from and written to RDF. Two health profiles exist:

| RDF profile (entry point) | Class | HealthDCAT-AP version | Metadata profile pack |
|---|---|---|---|
| `euro_health_dcat_ap` | `EuropeanHealthDCATAPProfile` | The portal's original model. | `gdi_current` |
| `euro_health_dcat_ap_r8` | `EuropeanHealthDCATAPR8Profile` | HealthDCAT-AP Release 8. | `healthdcat_r8` |

The R8 profile builds on the first and overrides only where R8 differs, so a row is the same for
both unless its "R8" column says otherwise. A deployment enables one or both packs and a harvest
source can pick one; see `docs/metadata-profiles.md` of the
`gdi-userportal-ckan-docker` repository. The full comparison with R8, property by property, is in
the [R8 gap analysis](healthdcat-ap-r8-gap-analysis.md).

Repeated values are written as repeated triples, not as an `rdf:List`.

### Dataset fields

| CKAN field | RDF property | Stored as | Both profiles | R8 |
|---|---|---|---|---|
| `analytics` | `healthdcatap:analytics` | list of IRIs | Also read as distributions. | Same. |
| `code_values` | `healthdcatap:hasCodeValues` | list | An IRI when the value starts with `http(s)`, otherwise a literal. | Always a literal: R8's range is literal. |
| `coding_system` | `healthdcatap:hasCodingSystem` | list | An IRI or a literal. | The node is typed `dct:Standard`; free text goes in a typed node as `dct:title`. |
| `health_category` | `healthdcatap:healthCategory` | list | An IRI or a literal. | A bare code of the health categories vocabulary is written as its IRI (see below); free text becomes a `skos:Concept` with a `skos:prefLabel`. |
| `health_theme` | `healthdcatap:healthTheme` | list | An IRI or a literal. | Same treatment as `health_category`. |
| `legal_basis` | `dpv:hasLegalBasis` | list | An IRI or a literal. | The node is typed `dpv:LegalBasis`. |
| `personal_data` | `dpv:hasPersonalData` | list | An IRI. | The node is typed `dpv:PersonalData`. |
| `purpose` | `dpv:hasPurpose` | list | An IRI or a literal. | The node is typed `dpv:Purpose`. |
| `population_coverage` | `healthdcatap:populationCoverage` | text | Free text; one value per language with the multilingual schema. | Same. |
| `min_typical_age`, `max_typical_age`, `number_of_records`, `number_of_unique_individuals` | `healthdcatap:minTypicalAge`, `maxTypicalAge`, `numberOfRecords`, `numberOfUniqueIndividuals` | integer | Written as `xsd:nonNegativeInteger`. | Same. |
| `quality_annotation` | `dqv:hasQualityAnnotation` | list of `body`, `target`, `motivated_by` | An `oa:Annotation` with `oa:hasBody`, `oa:hasTarget`, `oa:motivatedBy`. Parsing keeps an annotation only when its body and target are `http(s)` IRIs. | The node is typed `dqv:QualityCertificate`, the range R8 requires. |
| `retention_period` | `healthdcatap:retentionPeriod` | list of `start`, `end` | A `dct:PeriodOfTime` with `dcat:startDate` and `dcat:endDate`. A distribution carries its own, as `resources[].retention_period`. | Same. |
| `hdab` | `healthdcatap:hdab` | list of agents | See agents below. | See agents below. |
| `trusted_data_holder` | `healthdcatap:trustedDataHolder` | boolean | Read and written. | Not an R8 property: not read, and the R8 pack has no field for it. |
| `dataset_status` | `adms:status` | choice | Read and written by the `euro_dcat_ap_nl` profile, which is in the `gdi_current` chain. | Not part of the R8 chain, and the R8 pack has no field for it. |

Fields only R8 has (`healthdcat_r8` pack):

| CKAN field | RDF property | Stored as | Notes |
|---|---|---|---|
| `alternative_title` | `dct:alternative` | list of text | |
| `has_structured_data` | `healthdcatap:hasStructuredData` | boolean | Written as `xsd:boolean`. R8 asks for variables when it is true; that is not checked. |
| `variables` | `healthdcatap:hasVariables` | nested list | A `csvw:TableGroup` (`dct:title`) holding `csvw:Table`s (`dct:title`, `dcat:keyword`, `csvw:url`) holding `csvw:Column`s (`csvw:name`, `csvw:title`, `dct:description`, `csvw:datatype`, `csvw:propertyUrl`). |
| `custodian` | `geodcatap:custodian` | agent | Same agent shape as `hdab`; the first value is written. |
| `hdab_coordinator` | `healthdcatap:hdabCoordinator` | agent | Same agent shape as `hdab`; the first value is written. |
| `related_resource` | `dct:relation` | list | In every profile this is also kept as a free extra by the shared DCAT-AP code; R8 makes it a schema field. |
| `source` | `dct:source` | list | As `related_resource`, for `dct:source`. |
| `resources[].access_services[].documentation` | `foaf:page` on the `dcat:DataService` | list of IRIs | |
| `qualified_attribution` | `prov:qualifiedAttribution` | list of `agent`, `role` | A `prov:Attribution` with one `prov:agent` and one `dcat:hadRole`. | `role` is a list (R8 allows one or more), written by the R8 profile itself; a schema that holds one role keeps the first, with a warning. |
| `qualified_relation` | `dcat:qualifiedRelation` | list of `uri`, `relation`, `role` | A `dcat:Relationship` with one `dct:relation` and one `dcat:hadRole`. | `relation` and `role` are lists (R8 allows one or more of each), sorted when read. A schema that holds one value keeps the first, with a warning. |
| `resources[].has_policy` | `odrl:hasPolicy` on the `dcat:Distribution` | IRI | At most one. The policy itself (its permissions and prohibitions) is not modelled: a policy that is a blank node is dropped with a warning, and a value that is not an IRI is not written. |

### Agents

`publisher`, `hdab`, `custodian` and `hdab_coordinator` are agents.

- **`euro_health_dcat_ap`**: a flat `foaf:Agent` with `vcard:hasEmail` and `foaf:homepage`, and the
  publisher note and type as `healthdcatap:publisherNote` and `healthdcatap:publisherType`.
- **`euro_health_dcat_ap_r8`**: every health agent has one `cv:ContactPoint` holding the email
  (`cv:email`), the contact page (`cv:contactPage`), the telephone (`cv:telephone`) and the opening
  hours (`cv:openingHours`, `cv:specialOpeningHoursSpecification`, as `time:TemporalEntity`). The
  publisher note is written as `dct:description`. The email, the contact page and the telephone are
  `0..n` on a contact point, so `email`, `url` and `telephone` are lists and every value is read and
  written (sorted, so a re-parse is stable). The flat terms of the other profile are still read, for
  agents that carry them, and are not written. When R8 gives an agent several contact points only the
  first is read, with a warning. A schema that holds one value in these subfields (the `gdi_current`
  agent) gets the first value, with a warning.

The subfields R8 adds to the contact point (`telephone`, `opening_hours`, `special_opening_hours`)
exist in the schema only when `healthdcat_r8` decides the shared agent fields; see the pack order in
the `profile_packs/README.md` of `ckanext-gdi-userportal`. A parsed value for a subfield the loaded schema lacks is dropped.

### Vocabulary IRIs (R8)

R8 requires concepts from the HealthDCAT-AP vocabularies under
`https://hdeu-dcat.data.health.europa.eu/resource/authority/`. The R8 profile writes a bare code as
the IRI in its vocabulary and leaves a value that is already an IRI (a Wikidata or ADMS one, for
example) as it is. There is no crosswalk from those to the new vocabularies.

| CKAN field | Vocabulary |
|---|---|
| `health_category` | `healthcategories` |
| `health_theme` | `health-theme` |
| `coding_system` | `coding-system` |
| `conforms_to` | `standard` |
| publisher type | `publisher-type` |
| `was_generated_by` activity type | `health-activity` |

### Values R8 allows several of

R8 allows several values for `dcat_type` (`dct:type`) and the landing page (`url`,
`dcat:landingPage`), and the R8 pack makes both lists: the profile reads every value, sorted, and
writes all of them. A schema that holds one value in them (`gdi_current` listed first) keeps the
first, with a warning. `identifier` stays single-valued (ADR 0001, Q3): the first value is kept and a
warning logged.

### Language-specific values

Several values in the same language (two `dct:provenance` statements in English, say) are all kept by
the R8 profile: they are joined, sorted, with a blank line, with a warning.

For language-specific literals (for example `population_coverage`, `publisher_note`, `title`,
resource `rights`), use a Fluent-aware schema: the dataset schema generated by the
`ckanext-gdi-userportal` profile packs, or `ckanext.dcat.schemas:health_dcat_ap_multilingual.yaml`
together with `ckanext.dcat.schemas:presets.yaml` and the Fluent presets.

!!! Note
    See [EuropeanHealthDCATAPProfile](https://github.com/ckan/ckanext-dcat/blob/master/ckanext/dcat/profiles/euro_health_dcat_ap.py)
    and `euro_health_dcat_ap_r8.py` in the same folder for implementation details.
