from .base import ADMS, URIRefOrLiteral
from .euro_dcat_ap_3 import EuropeanDCATAP3Profile


class EuropeanDCATAPNLProfile(EuropeanDCATAP3Profile):
    """
    An RDF profile implementing DCAT-AP-NL 3.0, the Dutch national extension
    of DCAT-AP 3 for data portals.

    https://docs.geostandaarden.nl/dcat/dcat-ap-nl30/

    Only properties that DCAT-AP-NL adds on top of DCAT-AP 3 (i.e. that
    don't already exist as a core DCAT-AP property) belong here. Properties
    where DCAT-AP-NL merely tightens cardinality or usage guidance on an
    existing DCAT-AP property stay in the base/DCAT-AP profiles.
    """

    def parse_dataset(self, dataset_dict, dataset_ref):

        # Call base method for DCAT-AP 3 properties
        dataset_dict = super(EuropeanDCATAPNLProfile, self).parse_dataset(
            dataset_dict, dataset_ref
        )

        # Data holder-submitted dataset status (distinct from CKAN's own
        # package state), using the "Dataset Status" NAL vocabulary. This
        # is a DCAT-AP-NL 3.0 addition: dcat:Dataset has no adms:status in
        # core DCAT-AP, which only defines it for dcat:Distribution.
        status = self._object_value(dataset_ref, ADMS.status)
        if status:
            dataset_dict["dataset_status"] = status

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        super(EuropeanDCATAPNLProfile, self).graph_from_dataset(
            dataset_dict, dataset_ref
        )

        self._add_triple_from_dict(
            dataset_dict,
            dataset_ref,
            ADMS.status,
            "dataset_status",
            _type=URIRefOrLiteral,
        )
