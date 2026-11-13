# Release 8 note: HealthDCAT-AP Release 8 specification

This is a short note on defects in the HealthDCAT-AP Release 8 specification files. They affect validation
against the specification; they are not defects of this extension. The mapping that the `euro_health_dcat_ap_r8`
profile implements is in [mapping-healthdcat.md](mapping-healthdcat.md).

## Defects of the specification files

* The conditional rule "if `hasStructuredData` is true, `hasVariables` is required" is written in a property
  shape without a path. That is not valid SHACL, and pyshacl stops on it.
* `sh:extends`, used on HealthAgent and HealthPublisherAgent, is not part of SHACL. Standard validators ignore
  it; the base Agent shape still applies through its own target class.
* The cardinality rules list "conforms to" as `RecommendEd` (capital E) for the restricted layer. The other
  layers say Optional.
* The Release 8 example does not validate cleanly. `dcat:byteSize` uses `xsd:nonNegativeInteger` where the
  DCAT-AP 3.0.0 shape wants `xsd:decimal`, and the class checks on vocabulary concepts need the EU
  vocabularies to be loaded.
* The import list has the DPV import commented out, so `dpv:LegalBasis`, `dpv:PersonalData` and `dpv:Purpose`
  must be present in the data itself.
* The SHACL imports DCAT-AP 3.0.0, while the specification page also links DCAT-AP 3.0.1.
* A comment in the non-public shapes says the publisher shape should also add `healthdcatap:trustedDataHolder`.
  No active shape or table row does, so the property is not validated.
* The property tables and the SHACL shapes disagree for these properties:
  * Distribution `dcat:byteSize`: the table says `xsd:nonNegativeInteger`, the shape `xsd:decimal`.
  * Distribution and Catalogue `dct:rights`: the table says 0..*, the shape allows at most one.
  * CatalogueRecord `dct:conformsTo`: the table says 0..*, the shape allows at most one.
  * ConceptScheme `dct:title`: the table says 0..*, the base shape requires at least one.
  * Identifier `skos:notation`: the table says 1, the shape allows at most one and requires none.
  * Publisher `dct:description`: the table says 0..*, HealthPublisherAgent allows at most one.
  * ContactPoint: the table says 0..n for all five properties, the shape requires `cv:email` or
    `cv:contactPage` at least once.
  * Kind: the table says 0..1 for each, the shape requires `vcard:hasURL` or `vcard:hasEmail` at least once.
  * `applicableLegislation` (1..* on Catalogue, Distribution and DatasetSeries) comes from the R8 shapes; the
    DCAT-AP base shapes have no minimum.
