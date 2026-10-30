# HealthDCAT-AP Release 8: gap analysis

Analysed on 2026-10-28 against `ckanext-dcat` commit `81bdc95`. No code or schema was changed for this analysis.

This page compares the current HealthDCAT-AP implementation with [HealthDCAT-AP Release 8 (R8)](https://data.health.europa.eu/healthdcat-ap/releases/release-8/), the current release.
Which earlier release the implementation matches does not matter; what matters is the exact difference with R8. It is meant as input for follow-up tickets and replaces no other documentation
(the existing field mapping is in [mapping-healthdcat.md](mapping-healthdcat.md); where it is out of date this is listed in section 5).

## Summary

- Across the 187 properties of R8 (57 on Dataset in section 1, 130 on the other 24 classes in section 2b), **82** are handled as R8 requires, **44** exist but differ from R8 (cardinality, datatype, node type, class or structure) and **61** are not supported (no schema field, or the whole class is missing). The table in "Gap overview by class" shows where.
- Dataset class: of the 57 Dataset properties in R8's per-layer cardinality rules, **34** are handled as R8 requires, **16** differ from R8 and **7** have no schema field. By R8's reuse flag, the CHANGED and NEW Dataset rows split into **20** on properties R8 marks extended (E) or profile specific (P) and **3** on properties reused as-is from DCAT-AP (A).
- Other classes (130 properties): the R8-specific rows (extended or profile specific) have **24** gaps; the rows that R8 reuses from DCAT-AP 3 as-is have **58** gaps, of which 7 sit in structures R8 introduced (the `hdabCoordinator` and `custodian` agents and `cv:ContactPoint`; they are flagged A because R8 reuses the DCAT-AP Agent properties `foaf:name` and `dct:type` and the Core Vocabularies contact point terms), 24 sit in Catalogue and CatalogueRecord (out of scope for now) and the remaining 27 are gaps against DCAT-AP 3 itself, not R8 changes. Classes that are not supported at all: CatalogueRecord, `cv:ContactPoint`, `time:TemporalEntity`, the CSVW classes (TableGroup, Table, Column), Concept, ConceptScheme and the `hdabCoordinator` and `custodian` agents; Catalogue, DataService and a few more are only partly supported. Two names need care: `cv:ContactPoint` is the CPSV-AP class R8 requires on every HealthAgent, and is not the dataset contact (`vcard:Kind`, supported); `time:TemporalEntity` is only used for opening hours, and dataset temporal coverage is supported (start and end dates through `dcat:startDate` and `dcat:endDate`; the `time:hasBeginning` and `time:hasEnd` variants are not written). Catalogue, CatalogueRecord and a standalone DataService are outside the intended scope for now (the DataService is nested in the Distribution); their rows are listed for completeness and are not defects.
- Of the mandatory properties (10 for the public and restricted layers, 14 for non-public), two are not met: `healthdcatap:hdab` (wrong agent shape) and `healthdcatap:hasStructuredData` (no field). Three more are only partly met: `dct:identifier`, `healthdcatap:healthCategory` and `dct:type`.
- The biggest structural change is the agent and contact model. Every R8 HealthAgent (`hdab`, `custodian`, `hdabCoordinator`, and the publisher) needs exactly one `cv:contactPoint`. The code never reads or writes `cv:` terms: agents are flat `foaf:Agent` nodes with `vcard:hasEmail`.
- New in R8 compared to the implementation: `custodian`, `hdabCoordinator`, `hasStructuredData`, `hasVariables` (nested CSVW), `dct:alternative`, and proper fields for `dct:source` and `dct:relation` (today only free extras).
- Controlled vocabularies: R8 requires the health vocabularies under `https://hdeu-dcat.data.health.europa.eu/resource/authority/`. That host appears nowhere in code, schemas or local data; health values today are Wikidata or ADMS IRIs.
- Nothing enforces cardinality today (the schema has no `required:`), and none of the 147 records (146 datasets and one series) in the local catalogue would conform to any layer. Recommendation: **warn about a missing mandatory property, never block** (section 3).
- Seven findings (D1 to D7; D7 is latent and D5 is documentation drift) found while verifying, independent of R8 (section 5): a contact `url` list is written back as a corrupted IRI (D1), and serializing a dataset whose distribution has a data service with a contact or publisher crashes (D6).
- Where the work lands: the dataset schema is generated from the profile packs of `ckanext-gdi-userportal`, not from the health schemas of this repository (those are used by tests only). Parsing and serializing is in this repository (`ckanext-dcat`); the FDP profile only adds tag sanitising and label resolution on top.

## Status after the `healthdcat_r8` profile

The tables below are the baseline of this analysis (commit `81bdc95`) and stay as they were. The
`healthdcat_r8` pack (`euro_health_dcat_ap_r8` profile, `ckanext-gdi-userportal` pack) changes the
status of **51 of the 187 rows**: SAME goes from 82 to **133**, CHANGED from 44 to **27**, NEW from 61 to **27**.
The profile builds on the HealthDCAT-AP profile, so the `gdi_current` chain does not change. The
shared fixes below are the exception (section 5, D1, D4 and D6).

**Checked** on R8's example (`example-healthdcat-dataset.ttl`, non-public) by parsing it, serializing the
result and validating that with pyshacl against each layer's shapes (public / restricted / non-public):

| | public | restricted | non-public |
|---|---|---|---|
| R8's own example | 9 | 9 | 8 |
| Round trip with the `gdi_current` chain (before) | 20 | 20 | 19 |
| Round trip with the R8 profile | 9 | 9 | 8 |

Every remaining result is one the original example has too: `dcat:byteSize` as `xsd:nonNegativeInteger`
against the `xsd:decimal` of the DCAT-AP shape, the class checks on the vocabulary concepts (the EU
vocabularies are not imported), two distribution counts, and the access rights of a non-public dataset
against the public and restricted shapes (section 6). R8's second example, AGORA, gives 0 / 1 / 1 as it is
and 2 / 3 / 3 after the round trip; the two extra are the class checks of its health category and theme,
whose concept definitions sit in the AGORA file itself.

**SAME now (51 rows).** Dataset (16): 2 alternative, 5 code values, 6 coding system, 8 contact point (D1),
10 custodian, 18 structured data, 19 variables, 26 legal basis, 31 personal data, 34 publisher,
35 purpose, 38 quality annotation, 40 related resource, 43 source, 52 hdab, 53 hdab coordinator.
Other classes (35): health data access body 1; hdab coordinator 1 to 3; publisher 1 and 2; custodian 1 to 3;
contact point 1 to 5; temporal entity 1 and 2; CSVW table group 1 and 2, table 1 to 4, column 1 to 5; data
service 1, 4 and 13 (D6) and 6; distribution 11 and 16; contact (`vcard:Kind`) 1 (D1); dataset series
2 (D1, through the same function, not run on a series).

**Still CHANGED, by decision.** Row 21 `identifier` stays single-valued (ADR 0001, Q3): the R8 profile
keeps the first value and logs a warning when it drops others. Rows 48 and 54, the distribution access
URL, download URL and rights, the data service title, description and endpoint description, and the
relationship role and relation became lists after this status was recorded; see
[mapping-healthdcat.md](mapping-healthdcat.md). The counts above predate that.

**Not done.** Four shared fixes that change `gdi_current` output and were not in the list of defects
to fix: the identifier `skos:notation` (rows 30, ID-1; D4 now gives a blank-node identifier its notation, an
IRI node still gives its IRI), the retention period dates typed as `xsd:date` (41, POT-3, POT-4), the
first activity only (51) and a byte size of 0 (DIST-5). D2 and D3 are not needed by an R8 property.
Deferred and untouched: licence type, Concept and ConceptScheme, the series subfields
(SER-5, SER-7). Catalogue and CatalogueRecord are out of scope. Existing Wikidata and ADMS values are not
mapped to the hdeu-dcat vocabularies (section 4): there is no crosswalk; only a bare authority code is
written as its IRI.

## Gap overview by class

Counts per R8 class. R8-specific gaps are CHANGED or NEW rows that R8 marks as extended (E) or profile specific (P); DCAT-AP 3 gaps are CHANGED or NEW rows that R8 reuses as-is (A). The reuse flag of the Dataset rows comes from R8's rules file, which carries it per property and per access level; it differs between levels for 12 properties, and a Dataset row counts as E or P when any level flags it so. Details per property are in sections 1 and 2b.

| Class | Support | Rows | SAME | CHANGED | NEW | R8-specific gaps (E, P rows) | DCAT-AP 3 gaps (A rows) |
|---|---|---|---|---|---|---|---|
| Dataset (section 1) | see section 1 | 57 | 34 | 16 | 7 | 20 | 3 |
| Agent (carrier: dataset `creator`) | supported | 2 | 2 | 0 | 0 | 0 | 0 |
| Health data access body (`healthdcatap:hdab`) | partly | 3 | 2 | 0 | 1 | 1 | 0 |
| Health data access body coordinator (`healthdcatap:hdabCoordinator`) | not supported | 3 | 0 | 0 | 3 | 1 | 2 |
| Publisher (`dct:publisher`) | partly | 4 | 2 | 1 | 1 | 2 | 0 |
| Custodian / data holder (`geodcatap:custodian`) | not supported | 3 | 0 | 0 | 3 | 1 | 2 |
| Catalogue (`dcat:Catalog`) | partly | 19 | 3 | 4 | 12 | 1 | 15 |
| Catalogue record (`dcat:CatalogRecord`) | not supported | 9 | 0 | 0 | 9 | 0 | 9 |
| Checksum (`spdx:Checksum`) | supported | 2 | 2 | 0 | 0 | 0 | 0 |
| Data service (`dcat:DataService`) | partly | 16 | 9 | 6 | 1 | 0 | 7 |
| Dataset series (`dcat:DatasetSeries`) | supported | 10 | 7 | 3 | 0 | 0 | 3 |
| Distribution (`dcat:Distribution`, also `adms:sample`, `healthdcatap:analytics`) | supported | 24 | 17 | 6 | 1 | 0 | 7 |
| Contact (`vcard:Kind`, dataset `dcat:contactPoint`) | supported | 2 | 1 | 1 | 0 | 1 | 0 |
| Licence document (`dct:LicenseDocument`) | partly | 1 | 0 | 0 | 1 | 0 | 1 |
| Location (`dct:Location`, dataset `spatial_coverage`) | supported | 3 | 3 | 0 | 0 | 0 | 0 |
| Relationship (`dcat:qualifiedRelation`) | partly | 2 | 0 | 2 | 0 | 0 | 2 |
| CSVW table group (`csvw:TableGroup`) | not supported | 2 | 0 | 0 | 2 | 2 | 0 |
| CSVW table (`csvw:Table`) | not supported | 4 | 0 | 0 | 4 | 4 | 0 |
| CSVW column (`csvw:Column`) | not supported | 5 | 0 | 0 | 5 | 5 | 0 |
| Contact point (`cv:ContactPoint`) | not supported | 5 | 0 | 0 | 5 | 2 | 3 |
| Concept (`skos:Concept`) | not supported | 1 | 0 | 0 | 1 | 0 | 1 |
| Concept scheme (`skos:ConceptScheme`) | not supported | 3 | 0 | 0 | 3 | 2 | 1 |
| Identifier (`adms:Identifier`, dataset `alternate_identifier`) | partly | 1 | 0 | 1 | 0 | 0 | 1 |
| Period of time (`dct:PeriodOfTime`, `temporal_coverage`, `retention_period`) | partly | 4 | 0 | 4 | 0 | 0 | 4 |
| Temporal entity (`time:TemporalEntity`, opening hours) | not supported | 2 | 0 | 0 | 2 | 2 | 0 |
| **Total** | | **187** | **82** | **44** | **61** | | |

## Sources and method

**R8 side.** The [R8 specification](https://data.health.europa.eu/healthdcat-ap/releases/release-8/), its SHACL files (public, restricted and non-public shapes, the recommended shapes, the range shapes and the controlled-vocabulary shapes, from the section *Validation of HealthDCAT-AP*), and `context/healthdcat-cardinality-rules.json`.
The last file holds the cardinality and requirement level (Mandatory, Recommended, Optional) per access level; the specification page loads it to rewrite the *Card* column when an access level is selected, so the static HTML only shows a baseline. R8 imports the DCAT-AP 3.0.0 shapes, which also require `dct:title` and `dct:description`. For the 33 Dataset properties that have a SHACL constraint, the rules file and the SHACL agree on all three layers.

**Implementation side.** `ckanext-dcat` (`master`, commit `81bdc95`), `ckanext-fairdatapoint` (`main`, `5a80198`) and `ckanext-gdi-userportal` (`main`, `ccf6ea2`). Line numbers below refer to these commits. The stack loads `fairdatapoint_dcat_ap` and `euro_dcat_ap_nl` as RDF profiles, with `scheming.dataset_fallback = false`.

**Verification.** Every property of the Dataset class (section 1) was traced through the parse and serialize code. The other 24 classes (section 2b) were traced by a code-explorer agent and spot-checked (section 7), not re-traced row by row. R8's own example dataset (`html/examples/example-healthdcat-dataset.ttl`, a non-public dataset) was then parsed and serialized again with the dev-stack profiles in a development stack (no database writes; the FDP label resolution, which writes term translations, was switched off in memory), and the output was validated with pyshacl against each layer's shapes.
Violations that the original example also produces were subtracted as baseline (section 6). The local catalogue was read through `package_search` (read only).

**Limits.** The development catalogue used for this analysis had 147 records: 146 datasets (145 plain DCAT-AP harvests and one health test dataset) and one dataset series; production data was not available. Vocabulary membership could not be validated offline.
The index and translation code in `ckanext-gdi-userportal` that reads health fields was not traced.

## How to read the tables

- **Card. per layer**: `min..max` followed by the requirement level: `M` mandatory, `R` recommended, `O` optional. One value means all three layers agree; otherwise `pub`, `res` and `np` give public, restricted and non-public. `R*` is a typo in R8's rules file (section 6).
- **Status**: **SAME** the field exists and parse/serialize handle it as R8 requires; **CHANGED** the field exists but differs from R8 (datatype, node type, class, structure) or loses or corrupts data for input shaped as R8 expects, including values that CKAN itself generates (for example the resource format `CSV`). Two cross-cutting parser defects, D3 (numeric fallbacks) and D4 (blank nodes read as plain strings), affect many rows and are noted in section 5 instead of changing each row's status; D1 and D6 are specific to one property and do count. A Dataset row takes the status of its nested class when the deviation hits the data R8's own example carries (contact `url`, retention-period dates, agent shape); other nested deviations are listed in 2b only; cardinality is only a reason when a field cannot hold the number of values R8 allows. Caveats about input that is not R8-shaped (a non-IRI where R8 wants an IRI, several values where R8 allows one) are noted in the row but leave the status SAME, because cardinality and vocabularies are not enforced anywhere (section 3); **NEW** no schema field, so the property is not supported (or only kept as a free extra).
- **Parse / Serialize** refer to `ckanext/dcat/profiles/`: `ap_base` = `euro_dcat_ap_base.py`, `ap2` / `ap3` = `euro_dcat_ap_2.py` / `euro_dcat_ap_3.py`, `health` = `euro_health_dcat_ap.py`, `scheming` = `euro_dcat_ap_scheming.py`, `rdf` = `base.py`, `processors` = `ckanext/dcat/processors.py`, `logic` = `ckanext/dcat/logic.py`, `fairdatapoint` = `ckanext-fairdatapoint`; `file:line`.
  `GS` = the dataset schema the stack loads (`ckanext-gdi-userportal/.../scheming/schemas/dataset_multilingual.yaml`, which also holds the Distribution `resource_fields`), `SS` = `dataset_series_multilingual.yaml` in the same directory; `GS:line`.
- **Origin** (section 2b): R8's reuse flag for the row: **A** reused as-is from DCAT-AP, **E** extended by R8, **P** profile specific.
- Cardinality is not enforced for any property (section 3), so "not enforced" is not repeated per row.

## 1. Dataset properties

All 57 properties of R8's Dataset cardinality rules, including the optional and recommended ones. Defect references (D1 to D7) point to section 5.

| # | R8 property | Card. per layer | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|
| 1 | access rights (`dct:accessRights`) | `1..1` M | `access_rights` | ap_base:195-200 (first value; a blank-node RightsStatement gives its label) | ap_base:597-603 (IRI plus `a dct:RightsStatement`; other text becomes a blank node with a label) | **SAME** | The value is not checked against the layer IRI; the conformance computation needs it. FDP harvest removes the default `<subject>#accessRights` before parsing. |
| 2 | alternative (`dct:alternative`) | `0..*` O | no field | not parsed | not serialized | **NEW** | Add a multi-valued text field and parse/serialize `dct:alternative` as a literal. |
| 3 | analytics (`healthdcatap:analytics`) | `0..*` R | `analytics` | health:53-57 (IRIs; also read as distributions) | health:266-268 (IRI) | **SAME** | A blank-node analytics node would be stored as its id string and written back as a bogus IRI (D4, cross-cutting). FDP harvest does not fetch the graphs of analytics nodes. |
| 4 | applicable legislation (`dcatap:applicableLegislation`) | `1..*` M | `applicable_legislation` | ap2:99-106 | ap2:276-305 (IRI or literal, `a eli:LegalResource` for IRIs) | **SAME** | Values that are not IRIs are written as literals; R8 requires IRIs. Catalogue, Distribution and DatasetSeries also require it (section 2). |
| 5 | code values (`healthdcatap:hasCodeValues`) | `0..*` R | `code_values` | health:106 | health:204 (IRI when the value starts with http/https) | **CHANGED** | R8 range is literal; http(s) values are written as IRIs and the local data holds IRIs. Decide: literal only, or accept the deviation. |
| 6 | coding system (`healthdcatap:hasCodingSystem`) | `0..*` R | `coding_system` | health:107 | health:205 (IRI or literal) | **CHANGED** | R8 requires the node to be typed `dct:Standard` and to come from the hdeu-dcat coding-system vocabulary; the type triple is not written and the schema help text asks for Wikidata URIs (section 4). |
| 7 | conforms to (`dct:conformsTo`) | pub `0..*` O · res `0..*` R* · np `0..*` O | `conforms_to` | ap_base:124 | ap_base:396 (class `dct:Standard`) | **SAME** | Vocabulary differs (section 4). FDP harvest removes conformsTo IRIs matching `/profile/`. R8 restricted layer lists it as `R*` (typo, section 6). |
| 8 | contact point (`dcat:contactPoint`) | pub `0..*` R · res `0..*` R · np `1..*` M | `contact` | scheming:229-232 via rdf:597-667 (vcard fn, hasEmail, hasUID, hasURL) | rdf:994-1028 (`a vcard:Kind`) | **CHANGED** | The `url` list is written as a corrupted IRI (defect D1). Mandatory in non-public; not enforced. |
| 9 | creator (`dct:creator`) | `0..*` O | `creator` | scheming:234-241 via health:347-388 | scheming:279 via health:390-440 | **SAME** | Same flat `foaf:Agent` model as publisher. |
| 10 | custodian (`geodcatap:custodian`) | `0..1` R | no field | not parsed | not serialized | **NEW** | Add an agent field shaped like R8's HealthAgent (exactly one `cv:contactPoint`), see section 2. |
| 11 | description (`dct:description`) | `1..*` M | `notes_translated` | ap_base:65-77 | ap_base:359-374 (one literal per language) | **SAME** |  |
| 12 | dataset distribution (`dcat:distribution`) | `1..*` M | `resources`, `distribution` | ap_base:225-233 (also reads `adms:sample` and `healthdcatap:analytics` as resources) | ap_base:619-628 | **SAME** | Blank-node ids are stored in `distribution` (`str()` at ap_base:225-227) and written back as bogus IRIs (ap_base:776-778); the Distribution resources themselves are parsed (ap_base:228-230) (D4, cross-cutting). Each Distribution needs `applicableLegislation` (section 2). |
| 13 | documentation (`foaf:page`) | pub `0..*` O · res `0..*` O · np `0..*` R | `documentation` | ap_base:125 | ap_base:397 (class `foaf:Document`) | **SAME** | A blank-node `foaf:Document` is stored as its id string and written back as a plain literal holding that id (D4, cross-cutting). |
| 14 | frequency (`dct:accrualPeriodicity`) | pub `0..1` O · res `0..1` O · np `0..1` R | `frequency` | ap_base:107,112-117 | ap_base:371 | **SAME** |  |
| 15 | geographical coverage (`dct:spatial`) | `0..*` O | `spatial_coverage` | scheming:66-95,219-224 | scheming:296-321 | **SAME** |  |
| 16 | has version (`dcat:hasVersion`) | `0..*` O | `has_version` | ap3:55-58 | ap3:114-118 (also `dct:hasVersion`, ap_base:399) | **SAME** | No test. |
| 17 | health category (`healthdcatap:healthCategory`) | `1..*` M | `health_category` | health:108 | health:206 | **SAME** | Mandatory. Empty in all 147 local records; vocabulary host differs (section 4). |
| 18 | structured data (`healthdcatap:hasStructuredData`) | `1..1` M | no field | not parsed | not serialized | **NEW** | Add a boolean field with parse/serialize as `xsd:boolean`. Mandatory; `true` requires at least one `hasVariables`. (`trusted_data_holder`, health:130-138, is the only boolean handling and is not an R8 property.) |
| 19 | variables (`healthdcatap:hasVariables`) | `0..*` R | no field | not parsed | not serialized | **NEW** | Nested CSVW TableGroup / Table / Column structure (section 2); needs a design for a nested field. |
| 20 | health theme (`healthdcatap:healthTheme`) | `0..*` R | `health_theme` | health:109 | health:207 | **SAME** | Vocabulary differs; the local data uses Wikidata (section 4). |
| 21 | identifier (`dct:identifier`) | `1..*` M | `identifier` | ap_base:105,112-117 (single value) | ap_base:368 (IRI for http(s) values; falls back to `guid`, `id`) | **CHANGED** | R8: one or more literals. Only one value is kept and http(s) values are written as IRIs. |
| 22 | in series (`dcat:inSeries`) | `0..*` O | `in_series` | processors.py:215-227 (series mapping) | ap3:162-185 | **SAME** | No R8 constraint; no test. |
| 23 | is referenced by (`dct:isReferencedBy`) | pub `0..*` O · res `0..*` O · np `0..*` R | `is_referenced_by` | ap2:99-106 | ap2:278-284 | **SAME** |  |
| 24 | keyword (`dcat:keyword`) | pub `0..*` R · res `0..*` R · np `1..*` M | `tags_translated`, `tags` | ap_base:86-91 | ap_base:376-383 | **SAME** | Mandatory in non-public. FDP harvest drops tags shorter than 2 or longer than 100 characters and replaces characters outside `A-Za-z0-9 -_.` (fairdatapoint `profiles.py:22-49,84-105`). |
| 25 | language (`dct:language`) | pub `0..*` O · res `0..*` O · np `0..*` R | `language` | ap_base:121 | ap_base:394 | **SAME** |  |
| 26 | legal basis (`dpv:hasLegalBasis`) | `0..*` R | `legal_basis` | health:110 | health:208 | **CHANGED** | R8 range requires the node to be typed `dpv:LegalBasis`; the type triple is not written. |
| 27 | modification date (`dct:modified`) | `0..1` O | `modified` | ap_base:104,112-117 | ap_base:386-390 (falls back to `metadata_modified`) | **SAME** |  |
| 28 | number of records (`healthdcatap:numberOfRecords`) | `0..1` R | `number_of_records` | health:94-100 (integer) | health:255-258,292-314 | **SAME** | Typed as `xsd:nonNegativeInteger`. Invalid input falls back to a plain literal or `xsd:integer` instead (D3). |
| 29 | number of unique individuals (`healthdcatap:numberOfUniqueIndividuals`) | `0..1` R | `number_of_unique_individuals` | health:94-100 | health:255-258,292-314 | **SAME** | As number of records (D3). |
| 30 | other identifier (`adms:identifier`) | `0..*` O | `alternate_identifier` | ap_base:123 (a blank-node `adms:Identifier` becomes its id string; `skos:notation` is not read) | ap3:133-141 (blank node plus `skos:notation`) | **CHANGED** | The parser reads the node (its IRI or blank-node id), not its `skos:notation`, so the identifier value is lost; in R8's example the identifier comes back as the node IRI instead of the notation. |
| 31 | personal data (`dpv:hasPersonalData`) | `0..*` R | `personal_data` | health:111 | health:209 (always an IRI) | **CHANGED** | R8 range requires the node to be typed `dpv:PersonalData`; the type triple is not written. |
| 32 | population coverage (`healthdcatap:populationCoverage`) | `0..*` R | `population_coverage` | health:112,117-128 | health:215-240 | **SAME** | With the multilingual schema one string per language is kept. |
| 33 | provenance (`dct:provenance`) | pub `0..*` O · res `0..*` O · np `1..*` M | `provenance` | ap_base:108,112-117 | ap_base:605-611 (one blank-node `dct:ProvenanceStatement`) | **CHANGED** | Non-public requires one or more statements. R8 models each statement as a `dct:ProvenanceStatement` node and the code writes a blank node, so R8's example statement IRI comes back as a blank node plus an empty `""@nl` label (round trip). The field holds one statement per language, which matches R8's own usage note (repeat per language), so the single-statement limit alone would not make the row CHANGED. |
| 34 | publisher (`dct:publisher`) | `0..1` R | `publisher` (with `publisher_note`, `publisher_type`) | scheming:234-241 via health:347-388 | scheming:276-278 via health:390-440 | **CHANGED** | R8 HealthPublisherAgent: exactly one `cv:contactPoint`; the note goes on `dct:description`. The code writes `vcard:hasEmail` on the agent and the note as `healthdcatap:publisherNote` (section 2). |
| 35 | purpose (`dpv:hasPurpose`) | `0..*` R | `purpose` | health:115 | health:211 | **CHANGED** | R8 range requires the node to be typed `dpv:Purpose`; the type triple is not written. |
| 36 | qualified attribution (`prov:qualifiedAttribution`) | `0..*` O | `qualified_attribution` | ap2:86-89,609-631 | ap2:327-343 | **SAME** |  |
| 37 | qualified relation (`dcat:qualifiedRelation`) | `0..*` O | `qualified_relation` | scheming:243-246,419-440 | scheming:323-325,442-491 | **SAME** |  |
| 38 | quality annotation (`dqv:hasQualityAnnotation`) | `0..*` R | `quality_annotation` | health:75-77,140-174 (kept only if body and target are http(s) IRIs) | health:316-344 (`oa:Annotation`) | **CHANGED** | R8 range class is `dqv:QualityCertificate`; the code writes `oa:Annotation`. |
| 39 | release date (`dct:issued`) | `0..1` O | `issued` | ap_base:103 | ap_base:387 (falls back to `metadata_created`) | **SAME** |  |
| 40 | related resource (`dct:relation`) | pub `0..*` O · res `0..*` O · np `0..*` R | no field (free extra `related_resource`) | ap_base:126 (kept as an extra) | ap_base:398 | **NEW** | Recommended in non-public. Add a schema field so it is a real property. |
| 41 | retention period (`healthdcatap:retentionPeriod`) | `0..1` R | `retention_period` (start, end) | health:80,176-194 | health:264,274-290 | **CHANGED** | Dates are forced to `xsd:date` (health:286, 288) although CKAN returns datetimes (`2019-01-01T00:00:00+00:00`), so the literal is ill-typed. One node per list item (R8: at most one). |
| 42 | sample (`adms:sample`) | `0..*` R | `sample` | ap3:39-41 | ap3:91-94 | **SAME** | FDP harvest does not fetch the graphs of sample nodes. |
| 43 | source (`dct:source`) | pub `0..*` O · res `0..*` O · np `0..*` R | no field (free extra `source`) | ap_base:129 (kept as an extra) | ap_base:401 | **NEW** | Recommended in non-public. The extra is stored (seen on one local dataset); add a schema field. |
| 44 | temporal coverage (`dct:temporal`) | pub `0..*` O · res `0..*` O · np `0..*` R | `temporal_coverage` | scheming:97-105,213-218 | scheming:281-294 | **SAME** |  |
| 45 | temporal resolution (`dcat:temporalResolution`) | pub `0..1` O · res `0..1` O · np `0..1` R | `temporal_resolution` | ap2:92-96 | ap2:266-273 | **SAME** |  |
| 46 | theme (`dcat:theme`) | `1..*` M | `theme` | ap_base:122 | ap_base:395 | **SAME** | Mandatory. |
| 47 | title (`dct:title`) | `1..*` M | `title_translated` | ap_base:65-77 | ap_base:354-374 | **SAME** |  |
| 48 | type (`dct:type`) | pub `0..*` O · res `0..*` O · np `1..*` M | `dcat_type` (single text) | ap_base:109,112-117 | ap_base:372 | **CHANGED** | Non-public requires one or more; only one value is kept (D4 also applies to blank-node concepts). |
| 49 | version (`dcat:version`) | `0..1` O | `version` | ap_base:54-63 and ap3:50-53 | ap3:104-112 | **SAME** |  |
| 50 | version notes (`adms:versionNotes`) | `0..*` O | `version_notes` | ap_base:106 | ap_base:370 | **SAME** | One value per language. |
| 51 | was generated by (`prov:wasGeneratedBy`) | `0..*` O | `was_generated_by` | ap2:65-84 (reads only the first activity) | ap2:307-325 (writes all) | **CHANGED** | R8: zero or more; parsing keeps only the first activity. |
| 52 | health data access body (`healthdcatap:hdab`) | `1..1` M | `hdab` | health:70-73 via health:347-388 | health:260 via scheming:338-417 | **CHANGED** | Mandatory, exactly one, shaped as HealthAgent with exactly one `cv:contactPoint`. The code writes every item, with the email as `vcard:hasEmail`. Empty in all 147 local records (section 3). |
| 53 | health data access body coordinator (`healthdcatap:hdabCoordinator`) | `0..1` O | no field | not parsed | not serialized | **NEW** | Add an agent field shaped like `hdab`. |
| 54 | landing page (`dcat:landingPage`) | pub `0..*` O · res `0..*` O · np `0..*` R | `url` (CKAN core) | ap_base:54-63 (single value) | ap_base:367 (IRI plus `a foaf:Document`) | **CHANGED** | R8: zero or more; only one value is kept. |
| 55 | spatial resolution (`dcat:spatialResolutionInMeters`) | `0..1` O | `spatial_resolution_in_meters` | ap2:119-136 | ap2:382-399 | **SAME** | R8: at most one; several values would be emitted. |
| 56 | minimum typical age (`healthdcatap:minTypicalAge`) | `0..1` R | `min_typical_age` | health:92-100 | health:252-258,292-314 | **SAME** | As number of records (D3). |
| 57 | maximum typical age (`healthdcatap:maxTypicalAge`) | `0..1` R | `max_typical_age` | health:93-100 | health:253-258,292-314 | **SAME** | As number of records (D3). |

## 2. R8 shape constraints on nested structures

R8 constrains the structures that hang off a dataset as well. This section summarises the constraints that R8's SHACL adds or changes; the full property tables of every class follow in section 2b.

| R8 shape | R8 constraint | Current implementation | Status | What is needed |
|---|---|---|---|---|
| HealthAgent (`healthdcatap:hdab`, `geodcatap:custodian`, `healthdcatap:hdabCoordinator`) | Exactly one `cv:contactPoint` of class `cv:ContactPoint`, on top of the DCAT-AP Agent shape (`foaf:name` at least one, `dct:type` at most one) | Flat `foaf:Agent` with name, homepage, type, identifier and spatial; the email is `vcard:hasEmail` on the agent. No `cv:` term is read or written, so the parsed `hdab` of R8's example keeps an empty email and url. | CHANGED (`hdab`), NEW (the others) | Model a nested contact point (email, contact page), parse `cv:contactPoint`, and decide whether to keep reading `vcard:hasEmail` for data that is already harvested. |
| HealthPublisherAgent (`dct:publisher`) | Exactly one `cv:contactPoint`; at most one `dct:description` (the publisher note) | `foaf:Agent` with `vcard:hasEmail`; the note is written as `healthdcatap:publisherNote` (on the agent only when the agent has a URI, and on the dataset) | CHANGED | As above; map the publisher note to `dct:description`. |
| ContactPoint (`cv:ContactPoint`) | `cv:email` (literal) or `cv:contactPage` (IRI), at least one; optional `cv:telephone`, `cv:openingHours`, `cv:specialOpeningHoursSpecification` | Not implemented | NEW | Part of the agent model above. |
| TemporalEntity (opening hours) | `dct:description` required; `cv:frequency` an IRI of class `dct:Frequency` | Not implemented | NEW | Only if opening hours are to be supported. |
| Kind (`vcard:Kind`, dataset `dcat:contactPoint`) | `vcard:hasURL` and `vcard:hasEmail` as IRIs, at most one of each, at least one of them | `vcard:Kind` with `fn`, `hasEmail` (mailto IRI), `hasUID` and `hasURL` | CHANGED | Fix defect D1 (a `url` list is written as a corrupted IRI); the at-least-one rule belongs in the conformance computation. |
| CSVW variables (`healthdcatap:hasVariables`) | TableGroup (at least one table, `dct:title`), Table (title, at least one column), Column (name, title, description, datatype; optional `propertyUrl`) | Not implemented; `csvw` appears only in two example files (`examples/dcat/dataset.ttl` and `dataset_health.ttl`) | NEW | Nested structure that needs a design for a nested field. |
| PeriodOfTime (`healthdcatap:retentionPeriod`) | At most one | One node per list item, dates forced to `xsd:date` although CKAN returns datetimes | CHANGED | See the retention period row in section 1. |
| Distribution (`dcat:distribution`, `adms:sample`, `healthdcatap:analytics`) | `dcatap:applicableLegislation`, one or more IRIs, on every Distribution | Resource field `applicable_legislation`, written with ELI typing when filled | SAME | None beyond filling the value. |
| Catalogue | `dcatap:applicableLegislation`, one or more IRIs | Catalogue output writes title, description, homepage, language and modified only | NEW | Only if catalogue output is used for R8. |
| DatasetSeries | `dcatap:applicableLegislation`, one or more IRIs | Written when the series has the field | SAME | None. |

## 2b. Property tables of all other classes

R8's own property tables for the 24 classes other than Dataset (130 properties), traced by code reading by a code-explorer agent and spot-checked (section 7), not re-run row by row. These tables are the same for all access levels (only the Dataset table changes with the access level). Where a class is carried by a dataset-level field (agents, contact, period of time, identifier, location, relationship), the CKAN field is that dataset-level field. Property URIs for R8's human-readable labels were derived from DCAT-AP 3, the R8 shapes and the R8 example; the least certain ones are listed in section 7.

### Agent (carrier: dataset `creator`)

Support: supported.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | name (`foaf:name`) | `1..*` | A | creator.name, name_translated GS:83-89 | rdf:555-576 via scheming:235-241 | scheming:365-383 | **SAME** | One value per language; same-language or untagged extras dropped on parse (rdf:563-565). |
| 2 | type (`dct:type`) | `0..1` | A | creator.type GS:99-100 | rdf:586 | scheming:387-393 | **SAME** | None. |

### Health data access body (`healthdcatap:hdab`)

Support: partly: name and type handled, `cv:contactPoint` missing.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | contact point (`cv:contactPoint (cv:ContactPoint)`) | `1` | P | NO FIELD (nearest: flat hdab.email/url GS:526-532) | NOT PARSED (health:71 reads only foaf:mbox, vcard:hasEmail, foaf:homepage on the agent; rdf:578-585) | NOT SERIALIZED (health:260 writes vcard:hasEmail and foaf:homepage on the agent; scheming:384-401) | **NEW** | No cv:contactPoint or cv:ContactPoint read or written; email and url sit flat on the agent. |
| 2 | name (`foaf:name`) | `1..*` | A | hdab.name, name_translated GS:519-524 | health:71 via rdf:555-576 | health:260 via health:400 via scheming:365-383 | **SAME** | All list items are written (first_only=False, health:260) although R8 allows one; schema is repeating_once (GS:514). |
| 3 | type (`dct:type`) | `0..1` | A | hdab.type GS:534-535 | rdf:586 | scheming:387-393 | **SAME** | None. |

### Health data access body coordinator (`healthdcatap:hdabCoordinator`)

Support: not supported (no field, no code).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | contact point (`cv:contactPoint`) | `1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | hdabCoordinator is not supported at all. |
| 2 | name (`foaf:name`) | `1..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No coordinator agent. |
| 3 | type (`dct:type`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No coordinator agent. |

### Publisher (`dct:publisher`)

Support: partly: no `cv:contactPoint`, note on a different predicate.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | contact point (`cv:contactPoint`) | `1` | P | NO FIELD (nearest: publisher.email/url GS:91-97) | NOT PARSED (rdf:578-585) | NOT SERIALIZED (scheming:384-401) | **NEW** | No cv:contactPoint; email and url are flat on the agent. |
| 2 | description (`dct:description`) | `0..*` | P | publisher.publisher_note GS:102-105 | health:347-388 (healthdcatap:publisherNote, health:367, health:378) | health:416-431 (only when the agent has a URI, health:408-414) | **CHANGED** | Predicate is healthdcatap:publisherNote, not dct:description; agents without a URI are skipped; R8 SHACL allows at most one. |
| 3 | name (`foaf:name`) | `1..*` | A | publisher.name, name_translated GS:83-89 | rdf:555-576 | scheming:365-383 | **SAME** | One value per language. |
| 4 | type (`dct:type`) | `0..1` | E | publisher.type GS:99-100 (plus publisher_type GS:107-111) | rdf:586 (health:382-386 for publisher_type) | scheming:387-393 (health:433-440 publisherType) | **SAME** | Also writes the legacy healthdcatap:publisherType for agents with a URI; no vocabulary check. |

### Custodian / data holder (`geodcatap:custodian`)

Support: not supported (no field, no code).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | name (`foaf:name`) | `1..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No custodian agent. |
| 2 | type (`dct:type`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No custodian agent. |
| 3 | contact point (`cv:contactPoint`) | `1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | `trusted_data_holder` (GS:482-492) is a boolean, not this. |

### Catalogue (`dcat:Catalog`)

Support: partly: root catalogue from site config (processors:322-338, ap_base:780-818); no schema, catalog_dict is empty (logic:44,63).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | applicable legislation (`dcatap:applicableLegislation`) | `1..*` | E | NO FIELD | NOT PARSED as catalogue (harvest-as-dataset only, ap2:98-106) | NOT SERIALIZED (ap_base:780-818) | **NEW** | R8 Catalog_Shape requires at least one; the root catalogue emits none. |
| 2 | catalogue (`dcat:catalog`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No dcat:catalog. |
| 3 | creator (`dct:creator`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 4 | dataset (`dcat:dataset`) | `0..*` | A | CKAN packages (paginated dcat_catalog_show, logic:34-48) | NOT PARSED (rdf:1457 is an inverse lookup only) | processors:417 (processors:450 sub-catalogue) | **SAME** | None. |
| 5 | description (`dct:description`) | `1..*` | A | config `ckan.site_description` fallback (ap_base:793-797) | harvest-as-dataset ap_base:66-77 | ap_base:792-797, 806-813 | **CHANGED** | Single untagged literal, omitted if the config is empty; R8 requires one or more. |
| 6 | geographical coverage (`dct:spatial`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 7 | has part (`dct:hasPart`) | `0..*` | A | no field; sub-catalogue built from per-dataset extras `source_catalog_*` | rdf:1470-1474, ap_base:206-211, rdf:1507-1550 | processors:429-463 | **CHANGED** | Only when `ckanext.dcat.expose_subcatalogs` is set (default false, not set in setup_scheming.sh). |
| 8 | homepage (`foaf:homepage`) | `0..1` | A | config `ckan.site_url` (ap_base:798) | harvest-as-dataset ap_base:214-222 | ap_base:798, 806-813 (URIRef) | **SAME** | None. |
| 9 | language (`dct:language`) | `0..*` | A | config `ckan.locale_default` (ap_base:802) | harvest-as-dataset ap_base:120-124 | ap_base:799-804 | **CHANGED** | Single value; the default `en` is a plain literal, the base Catalog_Shape wants a blank node or IRI. |
| 10 | licence (`dct:license`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 11 | modification date (`dct:modified`) | `0..1` | A | derived: latest dataset metadata_modified (rdf:1403-1423) | harvest-as-dataset ap_base:104-117 | ap_base:815-818 | **SAME** | None. |
| 12 | publisher (`dct:publisher`) | `1..1` | A | NO FIELD | NOT PARSED as catalogue (scheming:235-241 when harvested as a dataset) | NOT SERIALIZED on the root (ap_base:780-818); only a sub-catalogue blank node (processors:465-488) | **NEW** | Mandatory (base Catalog_Shape min 1); the root emits no dct:publisher. |
| 13 | record (`dcat:record`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 14 | release date (`dct:issued`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED (only modified, ap_base:815-818) | **NEW** | None. |
| 15 | rights (`dct:rights`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | R8 allows several, base SHACL at most one. |
| 16 | service (`dcat:service`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 17 | temporal coverage (`dct:temporal`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 18 | themes (`dcat:themeTaxonomy`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 19 | title (`dct:title`) | `1..*` | A | config `ckan.site_title` fallback (ap_base:791) | harvest-as-dataset ap_base:66-77 | ap_base:790-797, 806-813 | **CHANGED** | Single untagged literal; R8 requires one or more. |

### Catalogue record (`dcat:CatalogRecord`)

Support: not supported (no code, no field).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | application profile (`dct:conformsTo`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | R8 allows several, base SHACL at most one. |
| 2 | change type (`adms:status`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 3 | description (`dct:description`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 4 | language (`dct:language`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 5 | listing date (`dct:issued`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 6 | modification date (`dct:modified`) | `1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | Mandatory (base shape min 1, max 1). |
| 7 | primary topic (`foaf:primaryTopic`) | `1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | Mandatory (base shape min 1, max 1). |
| 8 | source metadata (`dct:source`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 9 | title (`dct:title`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

### Checksum (`spdx:Checksum`)

Support: supported via the flat resource fields `hash` and `hash_algorithm`.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | algorithm (`spdx:algorithm`) | `1` | A | resource hash_algorithm GS:730-732 | ap_base:325-329 | ap_base:762-772 | **SAME** | Written only when `hash` is set (ap_base:751) and the algorithm is filled (ap_base:762); a literal if not http. |
| 2 | checksum value (`spdx:checksumValue`) | `1` | A | resource hash GS:726-728 | ap_base:330-331 | ap_base:751-760 (xsd:hexBinary) | **SAME** | No hex validation; several checksum nodes collapse to the last on parse (ap_base:325-331). |

### Data service (`dcat:DataService`)

Support: partly: only as a nested `dcat:accessService` of a Distribution (resource field access_services GS:827-973, ap2:177-257, ap2:470-590); no catalogue-level `dcat:service`.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | access rights (`dct:accessRights`) | `0..1` | A | access_services.access_rights GS:861-864 | ap2:191 | ap2:497 | **CHANGED** | R8 expects a `dct:RightsStatement` node; the code writes an IRI or a literal and no node (the dataset-level access rights does write one). |
| 2 | applicable legislation (`dcatap:applicableLegislation`) | `0..*` | A | access_services.applicable_legislation GS:910-914 | ap2:210 | ap2:535 | **SAME** | Non-http values become literals where the shape wants IRIs. |
| 3 | conforms to (`dct:conformsTo`) | `0..*` | A | access_services.conforms_to GS:866-869 | ap2:205 | ap2:530 | **SAME** | None. |
| 4 | contact point (`dcat:contactPoint (vcard:Kind)`) | `0..*` | A | access_services.contact GS:916-944 (repeating_once) | ap2:228-230 (list of dicts) | ap2:517-519 | **CHANGED** | Defect D6: parse yields a list, serialize calls `.get` on it and crashes (confirmed). |
| 5 | description (`dct:description`) | `0..*` | A | access_services.description GS:838-841 | ap2:192 (single, language dropped, rdf:259-271) | ap2:506 (literal, no language) | **CHANGED** | Single untagged value; R8 allows several. |
| 6 | documentation (`foaf:page`) | `0..*` | A | NO FIELD (no documentation subfield, GS:834-973) | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 7 | endpoint description (`dcat:endpointDescription`) | `0..*` | A | access_services.endpoint_description GS:849-850 | ap2:189 (single) | ap2:500-505 | **CHANGED** | Single value; R8 allows several. |
| 8 | endpoint URL (`dcat:endpointURL`) | `1..*` | A | access_services.endpoint_url GS:852-854 | ap2:203 | ap2:576-586 | **SAME** | None. |
| 9 | format (`dct:format`) | `0..*` | A | access_services.format GS:871-874 | ap2:206 | ap2:531 | **SAME** | Free text becomes a literal. |
| 10 | keyword (`dcat:keyword`) | `0..*` | A | access_services.keyword, keyword_translated GS:900-908 | ap2:218-226 | ap2:550-572 | **SAME** | None. |
| 11 | landing page (`dcat:landingPage`) | `0..*` | A | access_services.landing_page GS:895-898 | ap2:209 | ap2:534 | **SAME** | None. |
| 12 | licence (`dct:license`) | `0..1` | A | access_services.license GS:958-960 | ap2:190 | ap2:496 | **SAME** | None. |
| 13 | publisher (`dct:publisher`) | `0..1` | A | access_services.publisher GS:951-955 | ap2:232-234 (list) | ap2:521-523 via rdf:904-992 | **CHANGED** | Defect D6: parse yields a list, serialize expects a dict and crashes (confirmed); also writes foaf:Organization plus foaf:Agent and foaf:mbox, no publisher note or `healthdcatap:publisherType`. |
| 14 | serves dataset (`dcat:servesDataset`) | `0..*` | A | access_services.serves_dataset GS:856-859 | ap2:204 | ap2:583 | **SAME** | None. |
| 15 | theme (`dcat:theme`) | `0..*` | A | access_services.theme GS:843-847 | ap2:211 | ap2:536 | **SAME** | Non-http values become literals where the shape wants IRIs. |
| 16 | title (`dct:title`) | `1..*` | A | access_services.title GS:834-836 | ap2:188 (single) | ap2:498 (literal, no language) | **CHANGED** | Single untagged value; R8 requires one or more. |

### Dataset series (`dcat:DatasetSeries`)

Support: supported (schema SS; parse processors:231-251, ap3:60-67; serialize ap3:96-102).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | applicable legislation (`dcatap:applicableLegislation`) | `1..*` | E | SS:39-43 | ap2:99-106 | ap2:285-292 | **SAME** | Non-http values become literals where the shape wants IRIs. |
| 2 | contact point (`dcat:contactPoint (vcard:Kind)`) | `0..*` | A | SS:45-65 (no uri or identifier subfields) | scheming:230-232, rdf:597-667 | scheming:271-274, rdf:994-1028 | **CHANGED** | hasURL written as an IRI of a Python list (D1); no uri or identifier subfields. |
| 3 | description (`dct:description`) | `1..*` | A | SS:30-37 notes_translated | ap_base:66-77 | ap_base:359-366 | **SAME** | None. |
| 4 | frequency (`dct:accrualPeriodicity`) | `0..1` | A | SS:67-75 | ap_base:107 | ap_base:371 | **SAME** | None. |
| 5 | geographical coverage (`dct:spatial`) | `0..*` | A | SS:77-86 (uri, text only) | scheming:66-95, scheming:219-224 | scheming:296-321 | **CHANGED** | Series schema has no geom, bbox or centroid subfields; the Location structure is reduced (whether the parsed keys are dropped or rejected by the series schema was not traced, section 7). |
| 6 | modification date (`dct:modified`) | `0..1` | A | SS:88-97 | ap_base:104 | ap_base:386-390 | **SAME** | None. |
| 7 | publisher (`dct:publisher`) | `0..1` | A | SS:99-136 (no uri, no name_translated) | scheming:235-241 | scheming:276-277 (first_only) | **CHANGED** | No uri subfield, so the agent IRI is expected to be lost and a blank node written (scheming:359-360; whether the series schema drops or rejects the key was not traced, section 7); publisher note and type need a uri (health:408-414). |
| 8 | release date (`dct:issued`) | `0..1` | A | SS:143-152 | ap_base:103 | ap_base:386-390 | **SAME** | None. |
| 9 | temporal coverage (`dct:temporal`) | `0..*` | A | SS:154-164 | scheming:97-105, scheming:213-218 | scheming:281-294 | **SAME** | None. |
| 10 | title (`dct:title`) | `1..*` | A | SS:12-23 | ap_base:66-77 | ap_base:354-374 | **SAME** | None. |

### Distribution (`dcat:Distribution`, also `adms:sample`, `healthdcatap:analytics`)

Support: supported (resource_fields GS:684-978; ap3:23-26, health:40-43).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | access service (`dcat:accessService`) | `0..*` | A | access_services GS:827-973 | ap2:180-257 | ap2:471-491 | **SAME** | See the DataService table. |
| 2 | access URL (`dcat:accessURL`) | `1..*` | A | access_url GS:762-765, url GS:685-687 | ap_base:259, ap_base:291-293 (single) | ap_base:644, ap_base:719-728 | **CHANGED** | Single value; no accessURL when `url` equals `download_url` and `access_url` is empty (ap_base:724-728). |
| 3 | applicable legislation (`dcatap:applicableLegislation`) | `1..*` | E | applicable_legislation GS:821-825 | ap2:170-175 | ap2:459-468 | **SAME** | Non-http values become literals where the shape wants IRIs. |
| 4 | availability (`dcatap:availability`) | `0..1` | A | availability GS:739-741 | ap2:148-155 | ap2:408 | **SAME** | None. |
| 5 | byte size (`dcat:byteSize`) | `0..1` | A | size GS:719-724 | ap_base:320-322 | ap_base:739-749, ap3:120-131 | **CHANGED** | A size of 0 is not emitted (ap_base:739). R8 says xsd:nonNegativeInteger while the DCAT-AP 3.0.0 shape says xsd:decimal (the code writes nonNegativeInteger). |
| 6 | checksum (`spdx:checksum`) | `0..1` | A | hash, hash_algorithm GS:726-732 | ap_base:325-331 | ap_base:750-774 | **SAME** | See the Checksum table. |
| 7 | compression format (`dcat:compressFormat`) | `0..1` | A | compress_format GS:711-713 | ap2:149 | ap2:409-414 | **SAME** | Free text becomes a literal where the shape wants a blank node or IRI. |
| 8 | description (`dct:description`) | `0..*` | A | description_translated GS:694-699 | ap_base:275-288 | ap_base:633-641 | **SAME** | None. |
| 9 | documentation (`foaf:page`) | `0..*` | A | documentation GS:809-813 | ap_base:296-303 | ap_base:652 | **SAME** | A blank-node Document is parsed to its id string and written back as a plain literal holding that id (D4, cross-cutting). |
| 10 | download URL (`dcat:downloadURL`) | `0..*` | A | download_url GS:768-771 | ap_base:260 (single) | ap_base:645 | **CHANGED** | Single value; R8 allows several. |
| 11 | format (`dct:format`) | `0..1` | A | format GS:701-704 | ap_base:305-317, rdf:790-861 | ap_base:713-717 | **CHANGED** | A normal CKAN value (for example CSV) is written as a plain literal; the shape wants a blank node or IRI. Harvested IRIs round-trip. |
| 12 | has policy (`odrl:hasPolicy`) | `0..1` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | `odrl` and `hasPolicy` not found in code. |
| 13 | language (`dct:language`) | `0..*` | A | language GS:803-807 | ap_base:296-303 | ap_base:653 | **SAME** | None. |
| 14 | licence (`dct:license`) | `0..1` | A | license GS:757-759 | ap_base:264 | ap_base:643, ap_base:667-685 | **SAME** | Always adds dct:type `adms/licencetype/UnknownIPR` on the licence node (ap_base:678-685). |
| 15 | linked schemas (`dct:conformsTo`) | `0..*` | A | conforms_to GS:815-819 | ap_base:296-303 | ap_base:654 | **SAME** | None. |
| 16 | media type (`dcat:mediaType`) | `0..1` | A | mimetype GS:706-709 | ap_base:305-312 | ap_base:707-711 | **CHANGED** | A guessed `text/csv` is written as a plain literal; the shape wants a blank node or IRI. |
| 17 | modification date (`dct:modified`) | `0..1` | A | modified GS:778-781 | ap_base:262 | ap_base:731-736 | **SAME** | None. |
| 18 | packaging format (`dcat:packageFormat`) | `0..1` | A | package_format GS:715-717 | ap2:150 | ap2:415-423 | **SAME** | Free text becomes a literal. |
| 19 | release date (`dct:issued`) | `0..1` | A | issued GS:773-776 | ap_base:261 | ap_base:731-736 | **SAME** | None. |
| 20 | rights (`dct:rights`) | `0..*` | A | rights GS:734-737 | ap_base:265 | ap_base:659-665 | **CHANGED** | A single RightsStatement blank node; R8 allows several, base SHACL at most one. |
| 21 | spatial resolution (`dcat:spatialResolutionInMeters`) | `0..1` | A | spatial_resolution_in_meters GS:799-801 | ap2:157-167 | ap2:436-457 | **SAME** | A list or comma string yields several triples. |
| 22 | status (`adms:status`) | `0..1` | A | status GS:743-755 | ap_base:263 | ap_base:642 | **SAME** | None. |
| 23 | temporal resolution (`dcat:temporalResolution`) | `0..1` | A | temporal_resolution GS:795-797 | ap2:151 | ap2:428-434 | **SAME** | None. |
| 24 | title (`dct:title`) | `0..*` | A | name_translated GS:689-692 | ap_base:275-288 | ap_base:630-640 | **SAME** | None. |

### Contact (`vcard:Kind`, dataset `dcat:contactPoint`)

Support: supported (rdf:597-667, rdf:994-1028) with a defect.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | contact page (`vcard:hasURL`) | `0..1` | P | contact.url GS:68-72 (multiple_text) | rdf:662-663 | rdf:1022-1028 | **CHANGED** | List passed to URIRef: the output is an IRI containing a Python list (D1). |
| 2 | email (`vcard:hasEmail`) | `0..1` | P | contact.email GS:60-62 | rdf:656-658 | rdf:1007-1014 | **SAME** | None. |

### Licence document (`dct:LicenseDocument`)

Support: partly: only a hardcoded `dct:type`.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | type (`dct:type`) | `0..*` | A | NO FIELD | NOT PARSED | ap_base:678-685 (hardcoded UnknownIPR, with a TODO in the code) | **NEW** | No licence-type field; a fixed value is written on every distribution licence. |

### Location (`dct:Location`, dataset `spatial_coverage`)

Support: supported (scheming:66-95, scheming:296-321).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | bbox (`dcat:bbox`) | `0..1` | A | spatial_coverage.bbox GS:257-258 | scheming:79-86, rdf:669-688 | scheming:313-321, rdf:1030-1100 | **SAME** | Invalid geometry is dropped on parse (rdf:676-688); one WKT literal by default. |
| 2 | centroid (`dcat:centroid`) | `0..1` | A | spatial_coverage.centroid GS:260-261 | scheming:79-86 | scheming:313-321 | **SAME** | Same caveat as bbox. |
| 3 | geometry (`locn:geometry`) | `0..1` | A | spatial_coverage.geom GS:254-255 | scheming:79-86 | scheming:313-321 | **SAME** | Same caveat; the series schema lacks these subfields (SS:79-85). |

### Relationship (`dcat:qualifiedRelation`)

Support: partly: single-valued role and relation (scheming:419-491).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | had role (`dcat:hadRole`) | `1..n` | A | qualified_relation.role GS:557-559 | scheming:436 (single), scheming:243-246 | scheming:484-491 | **CHANGED** | Single value; R8 allows several. |
| 2 | relation (`dct:relation`) | `1..n` | A | qualified_relation.relation GS:553-555 | scheming:437 (single) | scheming:476-483 | **CHANGED** | Single value; R8 allows several. |

### CSVW table group (`csvw:TableGroup`)

Support: not supported (`csvw` not found in code).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | table (`csvw:table`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | `healthdcatap:hasVariables` is not supported. |
| 2 | title (`dct:title`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

### CSVW table (`csvw:Table`)

Support: not supported.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | column (`csvw:column`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 2 | keyword (`dcat:keyword`) | `0..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 3 | title (`dct:title`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 4 | url (`csvw:url`) | `0..1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

### CSVW column (`csvw:Column`)

Support: not supported.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | datatype (`csvw:datatype`) | `1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 2 | description (`dct:description`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 3 | name (`csvw:name`) | `1..1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 4 | property URL (`csvw:propertyUrl`) | `0..1` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 5 | title (`csvw:title`) | `1..n` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

### Contact point (`cv:ContactPoint`)

Support: not supported (closest is `vcard:Kind`).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | availability restriction (`cv:specialOpeningHoursSpecification (derived from ContactPoint_Shape)`) | `0..n` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 2 | contact page (`cv:contactPage`) | `0..n` | E | NO FIELD (nearest: contact.url GS:68-72, hdab.url GS:530-532) | NOT PARSED | NOT SERIALIZED | **NEW** | vcard:hasURL or foaf:homepage is written instead. |
| 3 | has email (`cv:email`) | `0..n` | E | NO FIELD (nearest: contact.email GS:60-62, hdab.email GS:526-528) | NOT PARSED | NOT SERIALIZED | **NEW** | vcard:hasEmail is written instead; the shape needs cv:email or cv:contactPage at least once. |
| 4 | has telephone (`cv:telephone`) | `0..n` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | No telephone field anywhere. |
| 5 | opening hours (`cv:openingHours`) | `0..n` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | Needs time:TemporalEntity, which is not supported. |

### Concept (`skos:Concept`)

Support: not supported (values are bare IRIs or literals).

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | preferred label (`skos:prefLabel`) | `1..n` | A | NO FIELD | NOT PARSED (rdf:267-270 reads the rdfs:label of any non-literal object, not prefLabel) | NOT SERIALIZED | **NEW** | FDP resolves labels of remote IRIs (schema:name, rdfs:label or skos:prefLabel, fairdatapoint/resolver.py:300) into the term-translation cache; this is not a skos:Concept model. |

### Concept scheme (`skos:ConceptScheme`)

Support: not supported.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | title (`dct:title`) | `0..*` | A | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | R8 allows none, the base CategoryScheme_Shape requires one. |
| 2 | preferred label (`skos:prefLabel`) | `0..*` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 3 | label (`rdfs:label (derived, uncertain)`) | `0..*` | P | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

### Identifier (`adms:Identifier`, dataset `alternate_identifier`)

Support: partly: written with `skos:notation`, parse is lossy.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | notation (`skos:notation`) | `1` | A | alternate_identifier (multiple_text) GS:277-285 | ap_base:123, ap_base:131-133 (reads the adms:Identifier node itself, rdf:377) | ap3:133-141 | **CHANGED** | Parse never reads skos:notation: the node IRI or blank-node id is stored and then re-emitted as the notation literal. |

### Period of time (`dct:PeriodOfTime`, `temporal_coverage`, `retention_period`)

Support: partly: start and end dates written, `time:` terms only read.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | beginning (`time:hasBeginning`) | `0..1` | A | folded into start (GS:228-230, GS:502-504) | scheming:42-53, rdf:496-516 (reads inXSDDate, DateTime, DateTimeStamp) | NOT SERIALIZED (time terms are only read, never written) | **CHANGED** | Read and collapsed into a start literal; never written back as time:Instant. |
| 2 | end (`time:hasEnd`) | `0..1` | A | folded into end (GS:232-234, GS:506-508) | scheming:42-53, rdf:496-516 | NOT SERIALIZED | **CHANGED** | Same as beginning. |
| 3 | end date (`dcat:endDate`) | `0..1` | A | temporal_coverage.end GS:232-234; retention_period.end GS:506-508 | scheming:38-39, health:185-193 | scheming:292-293 (typed by value); health:287-288 (forced xsd:date) | **CHANGED** | The retention path forces xsd:date; datetime_flex yields datetimes. |
| 4 | start date (`dcat:startDate`) | `0..1` | A | temporal_coverage.start GS:228-230; retention_period.start GS:502-504 | scheming:38-39, health:185-193 | scheming:290-291; health:285-286 (forced xsd:date) | **CHANGED** | Same as end date. |

### Temporal entity (`time:TemporalEntity`, opening hours)

Support: not supported.

| # | R8 property | Card. | Origin | CKAN field | Parse | Serialize | Status | What is needed |
|---|---|---|---|---|---|---|---|---|
| 1 | description (`dct:description`) | `1..n` | E | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |
| 2 | frequency (`cv:frequency`) | `0..n` | E | NO FIELD | NOT PARSED | NOT SERIALIZED | **NEW** | None. |

## 3. Mandatory properties and how to handle a missing one

The layer follows from `dct:accessRights` (`PUBLIC`, `RESTRICTED`, `NON_PUBLIC`). Public and restricted share the same 10 mandatory properties; non-public adds `dcat:contactPoint`, `dcat:keyword`, `dct:provenance` and `dct:type`.

| Mandatory property | Layers | CKAN field | State | Gap |
|---|---|---|---|---|
| `dct:accessRights` | all | `access_rights` | Met | Not checked against the layer IRI |
| `dcatap:applicableLegislation` | all | `applicable_legislation` | Met, caveat | Non-IRI values written as literals |
| `dcat:distribution` | all | `resources`, `distribution` | Met, caveat | Blank-node ids stored in `distribution` and written back as bogus IRIs; the Distribution resources themselves are parsed (D4) |
| `dct:title` | all | `title_translated` | Met | None |
| `dct:description` | all | `notes_translated` | Met | None |
| `dct:identifier` | all | `identifier` | Partly | Single value only |
| `dcat:theme` | all | `theme` | Met | None |
| `healthdcatap:healthCategory` | all | `health_category` | Partly | Field works, but is empty in all local data and the vocabulary host is not in use |
| `healthdcatap:hdab` | all | `hdab` | **Not met** | No `cv:contactPoint`; every item written (R8: exactly one) |
| `healthdcatap:hasStructuredData` | all | none | **Not met** | No field, parse or serialize |
| `dcat:contactPoint` | non-public | `contact` | Met, caveat | Contact `url` list defect (D1) |
| `dcat:keyword` | non-public | `tags_translated` | Met, caveat | FDP harvest drops or rewrites some keywords |
| `dct:provenance` | non-public | `provenance` | Met, caveat | Statement node written as a blank node (IRI lost) |
| `dct:type` | non-public | `dcat_type` | Partly | Single value only |

Every HealthAgent (hdab, and the publisher, custodian and coordinator when present) also needs its `cv:contactPoint`, which is not met anywhere. When `hasStructuredData` is true, at least one `hasVariables` is required.

**Conformance today.** None of the 147 records (146 datasets and one series) in the local catalogue would conform to any layer: `hdab` and `health_category` are empty on all of them and `hasStructuredData` has no field. Production data may differ.

**Recommendation: warn, never block.** This is an opinion, not a fact of the codebase.

- Nothing enforces cardinality today: the dataset schema has no `required:` and harvest parsing is tolerant. Blocking would be a new enforcement mechanism.
- Blocking would reject every dataset held locally, and harvested sources are third-party.
- Conformance is computed per layer from the mandatory properties, so a missing mandatory property is a computed fact ("not conformant to NON_PUBLIC, missing X and Y"), not a reason to reject.
- A warning can be a log line plus a computed list of missing properties at parse or index time; a missing recommended property needs no more than an informational note. Stored data stays untouched.

Where the warning is shown (harvest log, harvest report, API) is still open.

## 4. Vocabulary IRIs

R8's controlled-vocabulary shapes require concepts from specific vocabularies. The local values come from one health dataset (the `dataset_health` test harvest) plus the plain DCAT-AP harvests.

| R8 property | R8 vocabulary | Current schema and code | Local data |
|---|---|---|---|
| `healthdcatap:healthCategory` | `hdeu-dcat.../authority/healthcategories` | Free list, no choices | No value in any dataset |
| `healthdcatap:healthTheme` | `hdeu-dcat.../authority/health-theme` | Free list | Wikidata entities |
| `healthdcatap:hasCodingSystem` | `hdeu-dcat.../authority/coding-system` | Free list; help text asks for Wikidata URIs | Wikidata property IRIs |
| `dct:conformsTo` | `hdeu-dcat.../authority/standard` | Free list | Wikidata entities |
| Publisher type (agent and dataset) | `hdeu-dcat.../authority/publisher-type` | Free | `http://purl.org/adms/publishertype/...` (also cited in `mapping-healthdcat.md`) |
| Health activity type (`prov:wasGeneratedBy`) | `hdeu-dcat.../authority/health-activity` | Free | Not analysed |
| `healthdcatap:hasCodeValues` | Literal | Written as an IRI when it starts with http(s) | IRIs (Wikidata, ICD-10 browser) |
| Theme, access right, language, frequency, file type, distribution status, availability | EU Publications Office authority tables | Free text or EU choice lists | Match (availability not present) |
| `dpv:hasLegalBasis`, `dpv:hasPersonalData`, `dpv:hasPurpose` | dpv classes, no host rule | Free lists | `https://w3id.org/dpv...` IRIs; the dpv type triple is not written |

`hdeu-dcat...` abbreviates `https://hdeu-dcat.data.health.europa.eu/resource/authority`. The host appears nowhere in code, schemas, presets or local data. The `healthdcatap:` namespace (`http://healthdataportal.eu/ns/health#`) is unchanged in R8, which notes that it is to be replaced once a HealthDCAT-AP namespace exists.

## 5. Defects found while verifying

These are independent of R8. D1 and the identifier loss (row 30 of section 1) surfaced in the round trip of R8's example, D2 and D6 by synthetic input, and D3, D4, D5 and D7 by reading the code (R8's example uses IRIs, not blank nodes, for the properties D4 covers). The round trip of the example (non-public layer) gives 19 results: 8 that the original example also produces (baseline, section 6) and 11 from the implementation: four missing `cv:contactPoint`, one missing `hasStructuredData`, and six missing class type triples (`dpv:LegalBasis`, `dpv:PersonalData` twice, `dpv:Purpose`, `dct:Standard`, `dqv:QualityCertificate`).

- **D1, contact `url` list corrupted.** `contact.url` is parsed as a list and passed to `URIRef` unchanged on output (`rdf:1022-1028`). R8's example `vcard:hasURL <https://healthdcat-ap.example.org/support/oncology-ehrs-2024>` comes back as `vcard:hasURL <['https://healthdcat-ap.example.org/support/oncology-ehrs-2024']>`.
- **D2, several blank-node agents overwrite each other.** With two blank-node agents on one property, every agent gets the `publisher_note` and `publisher_type` of the last blank-node agent that has one (`health:363-375`).
- **D3, numeric fallbacks.** Invalid values fall back to a plain literal, and `-1` given as an integer (parser output) becomes `xsd:integer` instead of `xsd:nonNegativeInteger`, and as a string (what `package_show` returns) it becomes a plain literal. A parsed integer `0` is not serialized (`if value:` at `health:302`); CKAN returns these fields as strings (`"0"` is written correctly), so this only matters for a dict coming straight from the parser.
- **D4, blank nodes read as plain strings (cross-cutting).** A blank node that is read as a plain value becomes its internal id string. This applies to every property read with `_object_value_list` (`rdf:377`) or `str()`: the dataset list at `ap_base:120-133` (`language`, `theme`, `adms:identifier`, `dct:conformsTo`, `foaf:page`, `dct:relation`, `dct:hasVersion`, `dct:isVersionOf`, `dct:source`), `is_referenced_by`, `applicable_legislation` and `hvd_category` (`ap2:99-106`), `dcat:hasVersion` (`ap3:55-58`), `dcat:distribution` (`ap_base:225-227`), `adms:sample` (`ap3:39`), analytics (`health:53-55`), `prov:wasGeneratedBy` (`ap2:69`), the health list at `health:105-125` (`code_values`, `coding_system`, `health_category`, `health_theme`, `legal_basis`, `personal_data`, `publisher_type`, `purpose`), and the Distribution and DataService lists (`ap_base:296-303`, `ap2:202-216`). On output the id comes back as a plain literal where the serializer uses `URIRefOrLiteral` (`rdf:79-96`), for example `language`, `foaf:page`, `dct:conformsTo`, `adms:sample`, `health_theme`, `legal_basis`, `purpose`, `health_category` and the coding system (`health:205-211`), and as a bogus IRI `URIRef(id)` where it uses `URIRef`: `theme`, `dcat:distribution` (`ap_base:776-778`), analytics (`health:266-268`), `personal_data` (`health:209`) and `prov:wasGeneratedBy` (`ap2:311`). Single-valued properties read with `_object_value` (for example `dct:type`, `rdf:259-270`) keep the `rdfs:label` of a labelled blank node and fall back to the id only when there is none. R8's shapes allow a blank node for most of these properties, but R8's own example uses IRIs, so the example does not trigger it. Because D4 touches many rows it is not counted in their status (see "How to read the tables").
- **D5, `mapping-healthdcat.md` out of date (fixed: the page was rewritten and now documents both health profiles).** It said list values use `rdf:List` (the code writes repeated triples), calls the quality annotation `healthdcatap:qualityAnnotation` (the code uses `dqv:hasQualityAnnotation`), describes `hdab` as a plain agent, and does not mention `trusted_data_holder` or `dataset_status`.
- **D6, data service contact or publisher crashes serialization.** The parser returns `contact` and `publisher` of a distribution's access service as lists (`ap2:228-234`), while the serializer passes them to `_add_contact_to_graph` and `_add_agent_to_graph`, which call `.get` on them (`rdf:995`, `rdf:913`). Serializing a dataset with such a data service raises `AttributeError: 'list' object has no attribute 'get'` and the whole dataset fails. Reproduced in the dev container with four separate synthetic datasets: no contact serializes, a contact list crashes, a publisher list crashes, and a contact given as a dict serializes; not checked against stored data, but the schema fields are `repeating_once` and the parser always yields lists.
- **D7, latent: harvest parse can fail on a catalogue without a publisher.** In `rdf:1541-1549` (`_extract_catalog_dict`) the variable `publisher` is assigned only when a publisher exists but is used unconditionally, so a catalogue without `dct:publisher` would raise `UnboundLocalError`. The function is called at parse time only (`ap_base:207-211`, guarded by `ckanext.dcat.expose_subcatalogs`, which is off by default); `_get_source_catalog` falls back to the root catalogue (`rdf:1455-1468`), so any harvested catalogue without a publisher would trigger it. The export path (`processors:429-490`) is not affected. Found by reading the code, not reproduced.

Two further round-trip observations are not counted as defects of a single property: every multilingual field writes an empty `""@nl` literal for a form language that has no value (`rdf:1327-1331`, visible for title, description and version notes in `step3_serialized.ttl`), and the IRI of a nested node in R8's example (temporal coverage, provenance statement, retention period, quality annotation, distribution rights, identifier) comes back as a blank node, so node identity is not preserved.

Checked and harmless: the scheming conversion runs twice per dataset in the AP3 profile (`ap3` calls `_parse_dataset_v2`, whose `super()` call reaches the scheming profile, and then calls the conversion again). The second pass is the one that moves the v2 fields to the dataset; skipping it loses four of them.

## 6. Issues in the R8 specification files

These affect anyone validating against R8 and are not defects of this implementation.

- The conditional rule "if `hasStructuredData` is true then `hasVariables` is required" sits in an `sh:property` block without `sh:path`. That is not valid SHACL and pyshacl aborts on it; moving the rule to the node shape (same meaning) fixes it.
- `sh:extends` (HealthAgent and HealthPublisherAgent) is not part of SHACL and is ignored by standard validators; the base Agent shape still applies through its own target class.
- The rules file lists `conforms to` in the restricted layer as `RecommendEd` (capital E); in the other layers it is Optional.
- R8's own example does not validate cleanly: `dcat:byteSize` uses `xsd:nonNegativeInteger` where the DCAT-AP 3.0.0 shape wants `xsd:decimal`, and class checks on vocabulary concepts need the EU vocabularies imported (the example itself yields 8 results offline).
- The import list has the dpv import commented out, so `dpv:LegalBasis`, `dpv:PersonalData` and `dpv:Purpose` types have to be present in the data itself.
- R8's SHACL imports DCAT-AP 3.0.0, while the specification page also links 3.0.1.
- R8's shapes carry a comment (`non-public-shapes.ttl:443`) that `HealthPublisherAgent_Shape` was meant to add `healthdcatap:trustedDataHolder` as well; no active shape or table row does, so the `trusted_data_holder` field in the schema has no R8 counterpart.
- Where R8's property tables and the SHACL shapes disagree on a non-Dataset class (the status in section 2b follows the R8 table):

  - Distribution `dcat:byteSize`: R8 table says `xsd:nonNegativeInteger`, the DCAT-AP 3.0.0 Distribution shape says `xsd:decimal`.
  - Distribution and Catalogue `dct:rights`: R8 table says 0..*, the shape allows at most one.
  - CatalogueRecord `dct:conformsTo`: R8 table says 0..*, the shape allows at most one.
  - ConceptScheme `dct:title`: R8 table says 0..*, the base shape requires at least one.
  - Identifier `skos:notation`: R8 table says 1, the shape allows at most one and requires none.
  - Publisher description: R8 table says 0..*, HealthPublisherAgent allows at most one `dct:description`.
  - ContactPoint: R8 table says 0..n for all five properties, the shape requires `cv:email` or `cv:contactPage` at least once.
  - Kind: R8 table says 0..1 for each, the shape requires `vcard:hasURL` or `vcard:hasEmail` at least once.
  - `applicableLegislation` 1..* on Catalogue, Distribution and DatasetSeries comes from the R8 shapes; the DCAT-AP base shapes have no minimum.

## 7. Not verified

- The section 2b trace was done by reading the code, not row by row; the spot-checks were: the absent terms (`CatalogRecord`, `odrl:hasPolicy`, `dcat:themeTaxonomy`, `time:TemporalEntity`, `cv:ContactPoint`, `csvw`, `skos:Concept`) have no hits in the code, the catalogue root writes only title, description, homepage, language and modified, a Distribution size of 0 is skipped, and the data service crash (D6) was reproduced. Refs outside these checks come from that trace.
- Production data (vocabulary IRIs in real harvests, how many datasets would conform to which layer).
- Controlled-vocabulary membership (needs the EU vocabularies, not available offline).
- The index and translation code in `ckanext-gdi-userportal` that reads health fields (`plugin.py`, `logic/action/translation_utils.py`).
- The harvest source `profile` setting, which is stored per source and not in the repository.
- Whether the DatasetSeries schema accepts the keys the parser produces: the series parse output is shaped by the dataset schema and validated against the series schema on create; whether unknown subfields are dropped or rejected was not traced.
- Whether a harvested catalogue survives package creation (the FDP catalogue parse discards the return value of `parse_dataset` and relies on in-place changes; off by default via `harvest_catalogs`).
- The preset definitions (`multiple_text`, `fluent_markdown`, `fluent_core_translated`, `select`) live in installed `ckanext-scheming` and `ckanext-fluent`; the trace relied on the explicit `validators:` lines.
- `datetime_flex` is assumed to yield ISO datetimes (as `package_show` showed for `retention_period`), which is why the forced `xsd:date` on the retention path is listed as a deviation.
- R8 property URIs derived from human labels with the least certainty: ConceptScheme label as `rdfs:label`; ContactPoint availability restriction as `cv:specialOpeningHoursSpecification`; CatalogueRecord change type as `adms:status` and listing date as `dct:issued`; Catalogue themes as `dcat:themeTaxonomy`; ContactPoint email as `cv:email` (the R8 shapes use `cv:email`, not `cv:hasEmail`).
- Distribution `format` and `mediaType` are CHANGED because the normal CKAN value (for example `CSV`) is written as a plain literal; harvested values that are IRIs round-trip correctly, so the verdict depends on the data source.

## 8. Suggested groupings for follow-up work

Suggestions only.

1. **Schema fields**: `hasStructuredData`, `hasVariables`, `custodian`, `hdabCoordinator`, `dct:alternative`, `dct:source`, `dct:relation` (in `ckanext-gdi-userportal`, and in the health schemas of this repository for tests).
2. **Agent and contact model**: nested `cv:ContactPoint` for hdab, custodian, coordinator and publisher; publisher note on `dct:description`.
3. **Serializer typing**: type triples for dpv terms, coding system and quality annotation (`dqv:QualityCertificate`); literal versus IRI for code values; multiple identifiers, types, provenance statements and activities.
4. **Conformance computation and warnings**, using the mandatory sets per layer (warn, never block).
5. **Vocabulary alignment** with the hdeu-dcat vocabularies, including what to do with Wikidata and ADMS values already harvested.
6. **Defect fixes** D1 to D4 and D6 (D7 is latent).
7. **Class support beyond Dataset** (section 2b): decide which unsupported classes are in scope for R8 conformance of this catalogue (Catalogue output fields, CatalogueRecord, DataService as a catalogue-level entity, `cv:ContactPoint`, TemporalEntity, CSVW), and which single-valued properties should become multi-valued (Distribution `downloadURL` and `accessURL`, DataService title and description, Relationship role and relation, Catalogue title, description and language).
8. **DCAT-AP 3 gaps** in the A rows of section 2b (for example `odrl:hasPolicy`, Distribution media type and format typing, `dct:rights` with several values), separate from the R8-specific work.
9. **Tests**: an R8 SHACL test and fixture (the existing `tests/shacl` has no HealthDCAT-AP shapes), using the R8 example.
10. **Documentation**: update `mapping-healthdcat.md` (D5).
