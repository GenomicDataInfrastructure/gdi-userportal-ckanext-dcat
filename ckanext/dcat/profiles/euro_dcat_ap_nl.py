from .base import ADMS, RDFProfile, URIRefOrLiteral


class EuropeanDCATAPNLProfile(RDFProfile):
    """
    An RDF profile implementing DCAT-AP-NL 3.0, the Dutch national extension
    of DCAT-AP 3 for data portals.

    https://docs.geostandaarden.nl/dcat/dcat-ap-nl30/

    Only properties that DCAT-AP-NL adds on top of DCAT-AP 3 (i.e. that
    don't already exist as a core DCAT-AP property) belong here. Properties
    where DCAT-AP-NL merely tightens cardinality or usage guidance on an
    existing DCAT-AP property stay in the base/DCAT-AP profiles.

    This is a purely additive profile (like `EuropeanDCATAPSchemingProfile`):
    it does not extend `EuropeanDCATAP3Profile` and does not call `super()`,
    so it never re-derives fields another profile already computed. This
    makes it safe to enable alongside any other profile, in any order, via
    `ckanext.dcat.rdf.profiles` or a harvest source's "profile" config -
    unlike subclassing the DCAT-AP chain, which would re-run (and can
    clobber) another profile's in-place mutations, e.g. per-resource
    retention_period set by EuropeanHealthDCATAPProfile.
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        # Data holder-submitted dataset status (distinct from CKAN's own
        # package state), using the "Dataset Status" NAL vocabulary. This
        # is a DCAT-AP-NL 3.0 addition: dcat:Dataset has no adms:status in
        # core DCAT-AP, which only defines it for dcat:Distribution.
        status = self._object_value(dataset_ref, ADMS.status)
        if status:
            dataset_dict["dataset_status"] = status

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        self._add_triple_from_dict(
            dataset_dict,
            dataset_ref,
            ADMS.status,
            "dataset_status",
            _type=URIRefOrLiteral,
        )
