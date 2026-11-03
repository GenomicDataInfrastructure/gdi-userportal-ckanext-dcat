import json
import logging
import re

from rdflib import DCAT, FOAF, PROV, RDF, RDFS, XSD, BNode, Literal, URIRef
from rdflib.namespace import DCTERMS as DCT
from rdflib.namespace import SKOS, Namespace

from ckanext.dcat.profiles.base import VCARD, CleanedURIRef
from ckanext.dcat.utils import resource_uri
from ckanext.dcat.profiles.euro_health_dcat_ap import (
    DPV,
    DQV,
    HEALTHDCATAP,
    OA,
    EuropeanHealthDCATAPProfile,
)

log = logging.getLogger(__name__)

# Core Vocabularies (the CPSV-AP contact point R8 requires on every health agent)
CV = Namespace("http://data.europa.eu/m8g/")
TIME = Namespace("http://www.w3.org/2006/time#")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
GEODCATAP = Namespace("http://data.europa.eu/930/")

namespaces = {
    "cv": CV,
    "time": TIME,
    "csvw": CSVW,
    "geodcatap": GEODCATAP,
    "dqv": DQV,
    "oa": OA,
}

# Agents R8 adds to the dataset: CKAN field and predicate
R8_AGENTS = (
    ("custodian", GEODCATAP.custodian),
    ("hdab_coordinator", HEALTHDCATAP.hdabCoordinator),
)

# Subfields R8 adds to the contact point of an agent. Parsed values for a subfield the
# loaded schema does not have are dropped: with gdi_current listed first its narrower
# definition of the agent fields wins.
CONTACT_POINT_SUBFIELDS = ("telephone", "opening_hours", "special_opening_hours")
AGENT_FIELDS = ("publisher", "hdab", "custodian", "hdab_coordinator")

# Predicates of the HealthDCAT-AP profile that R8 replaces on an agent
LEGACY_AGENT_PREDICATES = (
    VCARD.hasEmail,
    FOAF.homepage,
    HEALTHDCATAP.publisherNote,
    HEALTHDCATAP.publisherType,
)

# R8 types what these properties point to (HealthDCAT-AP R8, ranges/range.ttl). Free text
# cannot have a class, so it becomes a typed node holding the text in the given property.
# An IRI gets the class too, where the data behind it usually carries none: the dpv
# vocabulary is not imported by R8's validation, and a coding system is a dct:Standard.
# A health category or theme IRI stays as it is: it is a concept of the EU vocabularies, which
# supply the class and the preferred label that a typed concept would be required to have.
TYPED_OBJECTS = (
    # predicate, class, property for free text, type an IRI
    (HEALTHDCATAP.hasCodingSystem, DCT.Standard, DCT.title, True),
    (DCT.conformsTo, DCT.Standard, DCT.title, True),
    (HEALTHDCATAP.healthCategory, SKOS.Concept, SKOS.prefLabel, False),
    (HEALTHDCATAP.healthTheme, SKOS.Concept, SKOS.prefLabel, False),
    (DPV.hasLegalBasis, DPV.LegalBasis, DCT.description, True),
    (DPV.hasPersonalData, DPV.PersonalData, DCT.description, True),
    (DPV.hasPurpose, DPV.Purpose, DCT.description, True),
)

# The controlled vocabularies R8 requires (gap analysis section 4), all under one host.
# A bare authority code of such a vocabulary is written as its IRI; a value that is already
# an IRI (Wikidata and ADMS ones included) or is not shaped like a code is left alone.
HDEU_AUTHORITY = "https://hdeu-dcat.data.health.europa.eu/resource/authority"
UPPERCASE_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_.\-]*$")
LOWERCASE_CODE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VOCABULARIES = {
    "healthcategories": (UPPERCASE_CODE, [HEALTHDCATAP.healthCategory]),
    "health-theme": (UPPERCASE_CODE, [HEALTHDCATAP.healthTheme]),
    "coding-system": (UPPERCASE_CODE, [HEALTHDCATAP.hasCodingSystem]),
    "standard": (UPPERCASE_CODE, [DCT.conformsTo]),
}
# Agents (publisher type), and the activity behind prov:wasGeneratedBy (health activity type)
PUBLISHER_TYPE = ("publisher-type", LOWERCASE_CODE)
HEALTH_ACTIVITY_TYPE = ("health-activity", UPPERCASE_CODE)
AGENT_PREDICATES = (DCT.publisher, DCT.creator, HEALTHDCATAP.hdab, GEODCATAP.custodian, HEALTHDCATAP.hdabCoordinator)

# R8 allows several values where the CKAN field holds one. The field stays single-valued
# (ADR 0001, Q3): the first value is kept and the others are dropped, with a warning.
SINGLE_VALUED = (
    (DCT.identifier, "identifier"),
    (DCT.type, "dcat_type"),
    (DCAT.landingPage, "url"),
)

BOOLEANS = {"true": True, "1": True, "false": False, "0": False}


class EuropeanHealthDCATAPR8Profile(EuropeanHealthDCATAPProfile):
    """
    A profile implementing HealthDCAT-AP Release 8.

    It builds on the HealthDCAT-AP profile and overrides only where R8 differs, so the
    fields and mapping R8 shares with it stay in one place. The CKAN field names are
    the profile-neutral ones; only the RDF mapping depends on the version.

    https://data.health.europa.eu/healthdcat-ap/releases/release-8/
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        dataset_dict = super().parse_dataset(dataset_dict, dataset_ref)

        # Not an R8 property, and the R8 schema has no field for it
        dataset_dict.pop("trusted_data_holder", None)

        alternative_titles = self._object_value_list(dataset_ref, DCT.alternative)
        if alternative_titles:
            dataset_dict["alternative_title"] = alternative_titles

        structured_data = self._object_value(dataset_ref, HEALTHDCATAP.hasStructuredData)
        if structured_data is not None and structured_data.lower() in BOOLEANS:
            dataset_dict["has_structured_data"] = BOOLEANS[structured_data.lower()]

        for key, predicate in R8_AGENTS:
            agents = self._agents_details(dataset_ref, predicate)
            if agents:
                dataset_dict[key] = agents

        variables = self._parse_variables(dataset_ref)
        if variables:
            dataset_dict["variables"] = variables

        for predicate, field in SINGLE_VALUED:
            self._warn_about_dropped_values(dataset_ref, predicate, field)
        self._warn_about_dropped_values_of_distributions(dataset_ref)

        self._parse_access_service_documentation(dataset_dict)
        self._make_contact_urls_single(dataset_dict)
        self._drop_what_the_schema_has_no_subfield_for(dataset_dict)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        super().graph_from_dataset(dataset_dict, dataset_ref)

        for prefix, namespace in namespaces.items():
            self.g.bind(prefix, namespace)

        for key, predicate in R8_AGENTS:
            self._add_agents(dataset_ref, dataset_dict, key, predicate, first_only=True)
        self._add_variables(dataset_ref, self._get_dict_value(dataset_dict, "variables"))

        self._add_list_triples_from_dict(
            dataset_dict,
            dataset_ref,
            [("alternative_title", DCT.alternative, None, Literal)],
        )

        structured_data = self._get_dict_value(dataset_dict, "has_structured_data")
        if structured_data not in (None, ""):
            self.g.add(
                (
                    dataset_ref,
                    HEALTHDCATAP.hasStructuredData,
                    Literal(str(structured_data).lower() in ("true", "1"), datatype=XSD.boolean),
                )
            )

        self._expand_vocabulary_codes(dataset_ref)
        self._type_the_objects(dataset_ref)
        self._write_code_values_as_literals(dataset_ref)
        self._write_quality_annotations_as_certificates(dataset_ref)

        for resource_dict in dataset_dict.get("resources", []):
            self._graph_from_resource(resource_dict)

    def _warn_about_dropped_values(self, subject_ref, predicate, field):
        values = {str(value) for value in self.g.objects(subject_ref, predicate)}
        if len(values) > 1:
            log.warning(
                "%s has %d values for %s but the field %s holds one; only the first is kept",
                subject_ref,
                len(values),
                predicate,
                field,
            )

    def _expand_vocabulary_codes(self, dataset_ref):
        for vocabulary, (code, predicates) in VOCABULARIES.items():
            for predicate in predicates:
                self._expand_codes(dataset_ref, predicate, vocabulary, code)

        vocabulary, code = PUBLISHER_TYPE
        for predicate in AGENT_PREDICATES:
            for agent_ref in list(self.g.objects(dataset_ref, predicate)):
                self._expand_codes(agent_ref, DCT.type, vocabulary, code)

        vocabulary, code = HEALTH_ACTIVITY_TYPE
        for activity_ref in list(self.g.objects(dataset_ref, PROV.wasGeneratedBy)):
            self._expand_codes(activity_ref, DCT.type, vocabulary, code)

    def _expand_codes(self, subject, predicate, vocabulary, code):
        for value in list(self.g.objects(subject, predicate)):
            # A bare code is a literal, or a relative IRI where the serializer wraps it in URIRef
            if isinstance(value, (Literal, URIRef)) and code.match(str(value)):
                self.g.remove((subject, predicate, value))
                self.g.add((subject, predicate, URIRef(f"{HDEU_AUTHORITY}/{vocabulary}/{value}")))

    def _type_the_objects(self, dataset_ref):
        for predicate, rdf_class, text_predicate, type_iris in TYPED_OBJECTS:
            for value in list(self.g.objects(dataset_ref, predicate)):
                if isinstance(value, URIRef):
                    if type_iris:
                        self.g.add((value, RDF.type, rdf_class))
                elif isinstance(value, Literal):
                    self.g.remove((dataset_ref, predicate, value))
                    node = BNode()
                    self.g.add((dataset_ref, predicate, node))
                    self.g.add((node, RDF.type, rdf_class))
                    self.g.add((node, text_predicate, value))

    def _write_code_values_as_literals(self, dataset_ref):
        """R8 gives hasCodeValues a literal range; the HealthDCAT-AP profile writes an IRI for http(s) values."""
        for value in list(self.g.objects(dataset_ref, HEALTHDCATAP.hasCodeValues)):
            if isinstance(value, URIRef):
                self.g.remove((dataset_ref, HEALTHDCATAP.hasCodeValues, value))
                self.g.add((dataset_ref, HEALTHDCATAP.hasCodeValues, Literal(str(value))))

    def _write_quality_annotations_as_certificates(self, dataset_ref):
        """R8's range for dqv:hasQualityAnnotation is dqv:QualityCertificate, not oa:Annotation."""
        for annotation_ref in self.g.objects(dataset_ref, DQV.hasQualityAnnotation):
            self.g.remove((annotation_ref, RDF.type, OA.Annotation))
            self.g.add((annotation_ref, RDF.type, DQV.QualityCertificate))

    # --- agents: every health agent has exactly one cv:contactPoint ---------------------

    def _agents_details(self, subject, predicate):
        """
        R8 puts the email and the contact page of an agent on a cv:ContactPoint, and the
        publisher note on dct:description. The flat vcard and foaf terms of HealthDCAT-AP
        are still read, for agents that carry them.
        """
        agents = super()._agents_details(subject, predicate)
        for agent, agent_ref in zip(agents, self.g.objects(subject, predicate)):
            self._read_contact_point(agent, agent_ref)
            if predicate == DCT.publisher:
                self._read_description_as_note(agent, agent_ref)
        return agents

    def _read_contact_point(self, agent, agent_ref):
        contact_points = list(self.g.objects(agent_ref, CV.contactPoint))
        if not contact_points:
            return
        if len(contact_points) > 1:
            log.warning(
                "%s has %d cv:contactPoint nodes but R8 allows one; only the first is read",
                agent_ref,
                len(contact_points),
            )
        contact_point = contact_points[0]

        email = self._without_mailto(self._first(contact_point, CV.email))
        if email:
            agent["email"] = email
        page = self._first(contact_point, CV.contactPage)
        if page:
            agent["url"] = page
        telephone = self._first(contact_point, CV.telephone)
        if telephone:
            agent["telephone"] = telephone
        self._warn_about_dropped_values(contact_point, CV.telephone, "telephone")

        for key, predicate in (
            ("opening_hours", CV.openingHours),
            ("special_opening_hours", CV.specialOpeningHoursSpecification),
        ):
            hours = self._temporal_entities(contact_point, predicate)
            if hours:
                agent[key] = hours

    def _read_description_as_note(self, agent, agent_ref):
        note = self._object_value(agent_ref, DCT.description, multilingual=True)
        if any(note.values()) and not any((agent.get("publisher_note") or {}).values()):
            agent["publisher_note"] = note

    def _add_agents(self, dataset_ref, dataset_dict, agent_key, rdf_predicate, first_only=False):
        agents = dataset_dict.get(agent_key)
        if agent_key not in AGENT_FIELDS:
            return super()._add_agents(dataset_ref, dataset_dict, agent_key, rdf_predicate, first_only)
        if not (isinstance(agents, list) and agents and self._not_empty_dict(agents[0])):
            return

        for agent in agents[:1] if first_only else agents:
            known = set(self.g.objects(dataset_ref, rdf_predicate))
            super()._add_agents(dataset_ref, {agent_key: [agent]}, agent_key, rdf_predicate)
            added = set(self.g.objects(dataset_ref, rdf_predicate)) - known
            agent_ref = CleanedURIRef(agent["uri"]) if agent.get("uri") else next(iter(added), None)
            if agent_ref is not None:
                self._write_r8_agent(agent_ref, agent)

    def _write_r8_agent(self, agent_ref, agent):
        for predicate in LEGACY_AGENT_PREDICATES:
            self.g.remove((agent_ref, predicate, None))

        note = agent.get("publisher_note")
        for lang, text in (note.items() if isinstance(note, dict) else [(None, t) for t in self._as_list(note)]):
            if text:
                self.g.add((agent_ref, DCT.description, Literal(text, lang=lang or None)))

        if any(self.g.objects(agent_ref, CV.contactPoint)):
            # The same agent in another role: R8 allows one contact point
            return

        email = self._first_value(agent.get("email"))
        page = self._first_value(agent.get("url"))
        telephone = self._first_value(agent.get("telephone"))
        hours = self._as_list_of_dicts(agent.get("opening_hours"))
        special_hours = self._as_list_of_dicts(agent.get("special_opening_hours"))
        if not (email or page or telephone or hours or special_hours):
            return

        contact_point = BNode()
        self.g.add((agent_ref, CV.contactPoint, contact_point))
        self.g.add((contact_point, RDF.type, CV.ContactPoint))
        if email:
            self.g.add((contact_point, CV.email, Literal(self._without_mailto(email))))
        if page:
            self.g.add((contact_point, CV.contactPage, URIRef(page)))
        if telephone:
            self.g.add((contact_point, CV.telephone, Literal(telephone)))
        self._add_temporal_entities(contact_point, CV.openingHours, hours)
        self._add_temporal_entities(contact_point, CV.specialOpeningHoursSpecification, special_hours)

    # --- opening hours -------------------------------------------------------------------

    def _temporal_entities(self, subject, predicate):
        entities = []
        for node in self.g.objects(subject, predicate):
            entity = {}
            descriptions = {
                lang: text
                for lang, text in self._object_value(node, DCT.description, multilingual=True).items()
                if text
            }
            if descriptions:
                entity["description_translated"] = descriptions
            frequency = self._first(node, CV.frequency)
            if frequency:
                entity["frequency"] = frequency
            if entity:
                entities.append(entity)
        return entities

    def _add_temporal_entities(self, subject, predicate, entities):
        for entity in entities:
            descriptions = entity.get("description_translated")
            frequency = self._first_value(entity.get("frequency"))
            if not (descriptions or frequency):
                continue
            node = BNode()
            self.g.add((subject, predicate, node))
            self.g.add((node, RDF.type, TIME.TemporalEntity))
            for lang, text in (descriptions or {}).items():
                if text:
                    self.g.add((node, DCT.description, Literal(text, lang=lang or None)))
            if frequency:
                self.g.add((node, CV.frequency, URIRef(frequency)))
                self.g.add((URIRef(frequency), RDF.type, DCT.Frequency))

    # --- variables: a CSVW table group, tables and columns -------------------------------

    def _parse_variables(self, dataset_ref):
        groups = []
        for group_ref in self.g.objects(dataset_ref, HEALTHDCATAP.hasVariables):
            group = {}
            self._put(group, "title_translated", self._translated(group_ref, DCT.title))

            tables = []
            for table_ref in self.g.objects(group_ref, CSVW.table):
                table = {}
                self._put(table, "title_translated", self._translated(table_ref, DCT.title))
                self._put(table, "keyword", sorted(str(k) for k in self.g.objects(table_ref, DCAT.keyword)))
                self._put(table, "url", self._first(table_ref, CSVW.url))

                columns = []
                for column_ref in self.g.objects(table_ref, CSVW.column):
                    column = {}
                    self._put(column, "name", self._first(column_ref, CSVW.name))
                    self._put(column, "title_translated", self._translated(column_ref, CSVW.title))
                    self._put(column, "description_translated", self._translated(column_ref, DCT.description))
                    self._put(column, "datatype", self._first(column_ref, CSVW.datatype))
                    self._put(column, "property_url", self._first(column_ref, CSVW.propertyUrl))
                    columns.append(column)
                # The graph has no order; sorting keeps the result stable
                self._put(table, "columns", sorted(columns, key=lambda c: c.get("name", "")))
                tables.append(table)
            self._put(group, "tables", tables)
            groups.append(group)
        return [group for group in groups if group]

    def _add_variables(self, dataset_ref, variables):
        for group in self._as_list_of_dicts(variables):
            group_ref = BNode()
            self.g.add((dataset_ref, HEALTHDCATAP.hasVariables, group_ref))
            self.g.add((group_ref, RDF.type, CSVW.TableGroup))
            self._add_translated(group_ref, DCT.title, group.get("title_translated"))

            for table in self._as_list_of_dicts(group.get("tables")):
                table_ref = BNode()
                self.g.add((group_ref, CSVW.table, table_ref))
                self.g.add((table_ref, RDF.type, CSVW.Table))
                self._add_translated(table_ref, DCT.title, table.get("title_translated"))
                for keyword in self._as_list(table.get("keyword")):
                    self.g.add((table_ref, DCAT.keyword, Literal(keyword)))
                if table.get("url"):
                    self.g.add((table_ref, CSVW.url, URIRef(table["url"])))

                for column in self._as_list_of_dicts(table.get("columns")):
                    column_ref = BNode()
                    self.g.add((table_ref, CSVW.column, column_ref))
                    self.g.add((column_ref, RDF.type, CSVW.Column))
                    if column.get("name"):
                        self.g.add((column_ref, CSVW.name, Literal(column["name"])))
                    self._add_translated(column_ref, CSVW.title, column.get("title_translated"))
                    self._add_translated(column_ref, DCT.description, column.get("description_translated"))
                    if column.get("datatype"):
                        self.g.add((column_ref, CSVW.datatype, Literal(column["datatype"])))
                    if column.get("property_url"):
                        self.g.add((column_ref, CSVW.propertyUrl, URIRef(column["property_url"])))

    # --- distributions and their data services -------------------------------------------

    def _access_service_node(self, service):
        if service.get("uri"):
            return CleanedURIRef(service["uri"])
        if service.get("access_service_ref"):
            return BNode(service["access_service_ref"])
        return None

    def _parse_access_service_documentation(self, dataset_dict):
        for resource_dict in dataset_dict.get("resources", []):
            services = resource_dict.get("access_services")
            is_json = isinstance(services, str)
            services = self._as_list_of_dicts(services)
            found = False
            for service in services:
                node = self._access_service_node(service)
                documentation = self._object_value_list(node, FOAF.page) if node is not None else []
                if documentation:
                    service["documentation"] = documentation
                    found = True
            if found and is_json:
                resource_dict["access_services"] = json.dumps(services)

    def _graph_from_resource(self, resource_dict):
        distribution_ref = CleanedURIRef(resource_uri(resource_dict))
        self._write_literals_as_nodes(distribution_ref, DCT["format"], DCT.MediaTypeOrExtent)
        self._write_literals_as_nodes(distribution_ref, DCAT.mediaType, DCT.MediaType)

        for service in self._as_list_of_dicts(resource_dict.get("access_services")):
            node = self._access_service_node(service)
            if node is None:
                continue
            for page in self._as_list(service.get("documentation")):
                self.g.add((node, FOAF.page, URIRef(page)))
            for value in list(self.g.objects(node, DCT.accessRights)):
                if isinstance(value, URIRef):
                    self.g.add((value, RDF.type, DCT.RightsStatement))
                else:
                    self.g.remove((node, DCT.accessRights, value))
                    statement = BNode()
                    self.g.add((node, DCT.accessRights, statement))
                    self.g.add((statement, RDF.type, DCT.RightsStatement))
                    self.g.add((statement, RDFS.label, value))

    def _write_literals_as_nodes(self, subject, predicate, rdf_class):
        """R8 wants an IRI or a blank node for a format or media type, not the plain text CKAN keeps."""
        for value in list(self.g.objects(subject, predicate)):
            if isinstance(value, Literal):
                self.g.remove((subject, predicate, value))
                node = BNode()
                self.g.add((subject, predicate, node))
                self.g.add((node, RDF.type, rdf_class))
                self.g.add((node, RDFS.label, value))

    def _warn_about_dropped_values_of_distributions(self, dataset_ref):
        for distribution_ref in self._distributions(dataset_ref):
            for predicate, field in (
                (DCAT.accessURL, "access_url"),
                (DCAT.downloadURL, "download_url"),
                (DCT.rights, "rights"),
            ):
                self._warn_about_dropped_values(distribution_ref, predicate, f"resources.{field}")
            for service_ref in self.g.objects(distribution_ref, DCAT.accessService):
                for predicate, field in (
                    (DCT.title, "title"),
                    (DCT.description, "description"),
                    (DCAT.endpointDescription, "endpoint_description"),
                ):
                    self._warn_about_dropped_values(service_ref, predicate, f"access_services.{field}")
        for relation_ref in self.g.objects(dataset_ref, DCAT.qualifiedRelation):
            for predicate, field in ((DCAT.hadRole, "role"), (DCT.relation, "relation")):
                self._warn_about_dropped_values(relation_ref, predicate, f"qualified_relation.{field}")

    def _drop_what_the_schema_has_no_subfield_for(self, dataset_dict):
        """With gdi_current listed first its narrower agent and data service fields win; keep the dict valid."""
        if not self._dataset_schema:
            return

        for key in AGENT_FIELDS:
            known = self._subfields(self._schema_field(key))
            for agent in self._as_list_of_dicts(dataset_dict.get(key)):
                for subfield in CONTACT_POINT_SUBFIELDS:
                    if subfield not in known:
                        agent.pop(subfield, None)

        known = self._subfields(self._schema_resource_field("access_services"))
        if "documentation" in known:
            return
        for resource_dict in dataset_dict.get("resources", []):
            services = resource_dict.get("access_services")
            if isinstance(services, list):
                for service in services:
                    if isinstance(service, dict):
                        service.pop("documentation", None)

    # --- contact points: one contact page ------------------------------------------------

    def _contact_url_is_single(self):
        """R8's vcard:Kind has at most one vcard:hasURL, so the url of a contact is one value.

        A schema that still lists the URLs (gdi_current listed first) keeps its list.
        """
        field = self._schema_field("contact")
        url = next((f for f in (field or {}).get("repeating_subfields", []) if f["field_name"] == "url"), None)
        return not (url and "scheming_multiple_text" in str(url.get("validators", "")))

    def _single_contact_url(self, contact):
        urls = self._as_list(contact.get("url"))
        if len(urls) > 1:
            log.warning(
                "contact %s has %d URLs but R8 allows one vcard:hasURL; only the first is kept",
                contact.get("uri") or contact.get("email") or "(unnamed)",
                len(urls),
            )
        return urls[0] if urls else ""

    def _make_contact_urls_single(self, dataset_dict):
        if not self._contact_url_is_single():
            return

        contacts = self._as_list_of_dicts(dataset_dict.get("contact"))
        for resource_dict in dataset_dict.get("resources", []):
            for service in self._as_list_of_dicts(resource_dict.get("access_services")):
                contacts.extend(self._as_list_of_dicts(service.get("contact")))

        for contact in contacts:
            if "url" in contact:
                contact["url"] = self._single_contact_url(contact)

    def _add_contact_to_graph(self, subject, predicate, contact):
        if isinstance(contact, dict) and "url" in contact and self._contact_url_is_single():
            contact = {**contact, "url": self._single_contact_url(contact)}
        super()._add_contact_to_graph(subject, predicate, contact)

    # --- small helpers -------------------------------------------------------------------

    @staticmethod
    def _subfields(field):
        return {f["field_name"] for f in (field or {}).get("repeating_subfields", [])}

    def _first(self, subject, predicate):
        """The first object as a string. Unlike _object_value this never swaps an IRI for its label."""
        value = next(iter(self.g.objects(subject, predicate)), None)
        return str(value) if value is not None else ""

    def _translated(self, subject, predicate):
        values = self._object_value(subject, predicate, multilingual=True)
        return {lang: text for lang, text in values.items() if text}

    def _add_translated(self, subject, predicate, translations):
        if isinstance(translations, dict):
            for lang, text in translations.items():
                if text:
                    self.g.add((subject, predicate, Literal(text, lang=lang or None)))

    @staticmethod
    def _put(target, key, value):
        if value:
            target[key] = value

    @staticmethod
    def _first_value(value):
        if isinstance(value, (list, tuple)):
            value = next((v for v in value if v), "")
        return value or ""

    @staticmethod
    def _as_list(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return [value] if value else []
        if isinstance(value, (list, tuple)):
            return [v for v in value if v]
        return [value] if value else []

    @classmethod
    def _as_list_of_dicts(cls, value):
        return [item for item in cls._as_list(value) if isinstance(item, dict)]
