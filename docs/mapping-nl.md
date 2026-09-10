## Mapping between CKAN fields and DCAT-AP-NL

This section defines how CKAN fields map to properties that [DCAT-AP-NL 3.0](https://docs.geostandaarden.nl/dcat/dcat-ap-nl30/)
adds on top of core DCAT-AP 3.0. These mappings are implemented in the `EuropeanDCATAPNLProfile`
class and extend the core DCAT-AP 3.0 logic.

Note that DCAT-AP-NL mostly tightens cardinality and usage guidance on properties that already
exist in core DCAT-AP (e.g. restricting `dct:accessRights` to three specific values); those stay
implemented in the base DCAT-AP profiles. Only properties DCAT-AP-NL adds that have no equivalent
in core DCAT-AP are listed here.

| DCAT Class   | RDF Property | CKAN Dataset Field | Stored as | Notes |
|--------------|--------------|---------------------|-----------|-------|
| dcat:Dataset | adms:status  | dataset_status      | value     | Status submitted by the data holder (e.g. under development, completed), distinct from CKAN's own internal package state. Values come from the [dataset-status](http://publications.europa.eu/resource/authority/dataset-status) NAL vocabulary. Core DCAT-AP 3.0 only defines `adms:status` for `dcat:Distribution` and `dcat:CatalogRecord`; DCAT-AP-NL 3.0 additionally defines it for `dcat:Dataset`. |

!!! Note
    See [EuropeanDCATAPNLProfile](https://github.com/ckan/ckanext-dcat/blob/master/ckanext/dcat/profiles/euro_dcat_ap_nl.py) for implementation details.
