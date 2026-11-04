import json
import uuid
import logging
import hashlib
import traceback

import sqlalchemy as sa

import ckan.plugins as p
import ckan.model as model

import ckan.lib.plugins as lib_plugins

from ckanext.harvest.model import HarvestObject, HarvestObjectExtra
from ckanext.harvest.logic.schema import unicode_safe
from ckanext.dcat.harvesters.base import DCATHarvester
from ckanext.dcat.harvesters.invalid_values import call_dropping_invalid_values
from ckanext.dcat.metadata_profiles import (
    MetadataProfileError,
    installed_rdf_profiles,
    resolve_source_profile,
)
from ckanext.dcat.processors import RDFParserException, RDFParser
from ckanext.dcat.interfaces import IDCATRDFHarvester

log = logging.getLogger(__name__)


class DCATRDFHarvester(DCATHarvester):

    def info(self):
        return {
            'name': 'dcat_rdf',
            'title': 'Generic DCAT RDF Harvester',
            'description': 'Harvester for DCAT datasets from an RDF graph'
        }

    _names_taken = []

    def _get_dict_value(self, _dict, key, default=None):
        '''
        Returns the value for the given key on a CKAN dict

        By default a key on the root level is checked. If not found, extras
        are checked, both with the key provided and with `dcat_` prepended to
        support legacy fields.

        If not found, returns the default value, which defaults to None
        '''

        if key in _dict:
            return _dict[key]

        for extra in _dict.get('extras', []):
            if extra['key'] == key or extra['key'] == 'dcat_' + key:
                return extra['value']

        return default

    def _get_guid(self, dataset_dict, source_url=None):
        '''
        Try to get a unique identifier for a harvested dataset

        It will be the first found of:
         * URI (rdf:about)
         * dcat:identifier
         * Source URL + Dataset name
         * Dataset name

         The last two are obviously not optimal, as depend on title, which
         might change.

         Returns None if no guid could be decided.
        '''
        guid = None

        guid = (
            self._get_dict_value(dataset_dict, 'uri') or
            self._get_dict_value(dataset_dict, 'identifier')
        )
        if guid:
            return guid

        if dataset_dict.get('name'):
            guid = dataset_dict['name']
            if source_url:
                guid = source_url.rstrip('/') + '/' + guid
        return guid

    def _mark_datasets_for_deletion(self, guids_in_source, harvest_job):
        '''
        Given a list of guids in the remote source, checks which in the DB
        need to be deleted

        To do so it queries all guids in the DB for this source and calculates
        the difference.

        For each of these creates a HarvestObject with the dataset id, marked
        for deletion.

        Returns a list with the ids of the Harvest Objects to delete.
        '''

        object_ids = []

        # Get all previous current guids and dataset ids for this source
        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id) \
                             .filter(HarvestObject.current==True) \
                             .filter(HarvestObject.harvest_source_id==harvest_job.source.id)

        guid_to_package_id = {}
        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = list(guid_to_package_id.keys())

        # Get objects/datasets to delete (ie in the DB but not in the source)
        guids_to_delete = set(guids_in_db) - set(guids_in_source)

        # Create a harvest object for each of them, flagged for deletion
        for guid in guids_to_delete:
            obj = HarvestObject(guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                extras=[HarvestObjectExtra(key='status',
                                                           value='delete')])

            # Mark the rest of this source's objects for this guid as not current (another source can
            # hold the same guid).
            model.Session.query(HarvestObject) \
                         .filter_by(guid=guid) \
                         .filter(HarvestObject.harvest_source_id == harvest_job.source.id) \
                         .update({'current': False}, False)
            obj.save()
            object_ids.append(obj.id)

        return object_ids

    def validate_config(self, source_config):
        if not source_config:
            return source_config

        source_config_obj = json.loads(source_config)
        if 'rdf_format' in source_config_obj:
            rdf_format = source_config_obj['rdf_format']
            if not isinstance(rdf_format, str):
                raise ValueError('rdf_format must be a string')
            supported_formats = RDFParser().supported_formats()
            if rdf_format not in supported_formats:
                raise ValueError('rdf_format should be one of: ' + ", ".join(supported_formats))

        # 'metadata_profile' (a profile pack) or 'profile' (a raw RDF profile chain), not both
        try:
            resolve_source_profile(source_config_obj, p.toolkit.config, installed_rdf_profiles())
        except MetadataProfileError as e:
            raise ValueError(str(e))

        return source_config

    def _source_rdf_profiles(self, harvest_job):
        '''
        The RDF profile chain the source is parsed with: the one of its 'metadata_profile' (or its raw
        'profile' chain), else the one of the deployment's main profile.

        Raises MetadataProfileError, with no fallback to the main profile: that would change the shape
        of the data unnoticed.
        '''
        source_config = json.loads(harvest_job.source.config) if harvest_job.source.config else {}
        resolved = resolve_source_profile(source_config, p.toolkit.config)
        log.info('Harvest source %s is parsed with metadata profile %s (RDF profiles: %s)',
                 harvest_job.source.id, resolved.name or '-', ' '.join(resolved.rdf_profiles))
        return resolved.rdf_profiles

    def gather_stage(self, harvest_job):

        log.debug('In DCATRDFHarvester gather_stage')

        rdf_format = None
        if harvest_job.source.config:
            rdf_format = json.loads(harvest_job.source.config).get("rdf_format")

        try:
            rdf_profiles = self._source_rdf_profiles(harvest_job)
        except MetadataProfileError as e:
            # A raise here would crash the consumer, so report it on the job and harvest nothing
            self._save_gather_error(
                'Harvest source %s: %s' % (harvest_job.source.id, e), harvest_job
            )
            return []

        # Get file contents of first page
        next_page_url = harvest_job.source.url

        guids_in_source = []
        object_ids = []
        last_content_hash = None
        self._names_taken = []
        # RDF URI of a dataset series -> its id and name. It is kept over the pages of a paged source,
        # so a dataset on a later page can point at a series on an earlier page.
        series_mapping = {}

        while next_page_url:
            for harvester in p.PluginImplementations(IDCATRDFHarvester):
                next_page_url, before_download_errors = harvester.before_download(next_page_url, harvest_job)

                for error_msg in before_download_errors:
                    self._save_gather_error(error_msg, harvest_job)

                if not next_page_url:
                    return []

            content, rdf_format = self._get_content_and_type(next_page_url, harvest_job, 1, content_type=rdf_format)

            content_hash = hashlib.md5()
            if content:
                content_hash.update(content.encode('utf8'))

            if last_content_hash:
                if content_hash.digest() == last_content_hash.digest():
                    log.warning('Remote content was the same even when using a paginated URL, skipping')
                    break
            else:
                last_content_hash = content_hash

            # TODO: store content?
            for harvester in p.PluginImplementations(IDCATRDFHarvester):
                content, after_download_errors = harvester.after_download(content, harvest_job)

                for error_msg in after_download_errors:
                    self._save_gather_error(error_msg, harvest_job)

            if not content:
                return []

            parser = RDFParser(profiles=rdf_profiles or None)

            try:
                parser.parse(content, _format=rdf_format)
            except RDFParserException as e:
                self._save_gather_error('Error parsing the RDF file: {0}'.format(e), harvest_job)
                return []

            for harvester in p.PluginImplementations(IDCATRDFHarvester):
                parser, after_parsing_errors = harvester.after_parsing(parser, harvest_job)

                for error_msg in after_parsing_errors:
                    self._save_gather_error(error_msg, harvest_job)

            if not parser:
                return []

            try:

                source_dataset = model.Package.get(harvest_job.source.id)

                object_ids += self._parse_and_collect(
                    parser.dataset_series(),
                    source_dataset,
                    harvest_job,
                    guids_in_source,
                    is_series=True,
                    series_mapping=series_mapping
                )

                object_ids += self._parse_and_collect(
                    parser.datasets(series_mapping),
                    source_dataset,
                    harvest_job,
                    guids_in_source,
                    is_series=False
                )
            except Exception as e:
                self._save_gather_error('Error when processsing dataset: %r / %s' % (e, traceback.format_exc()),
                                        harvest_job)
                return []

            # get the next page
            next_page_url = parser.next_page()

        # Check if some datasets need to be deleted
        object_ids_to_delete = self._mark_datasets_for_deletion(guids_in_source, harvest_job)

        object_ids.extend(object_ids_to_delete)

        return object_ids

    def fetch_stage(self, harvest_object):
        # Nothing to do here
        return True

    def import_stage(self, harvest_object):

        log.debug('In DCATRDFHarvester import_stage')

        status = self._get_object_extra(harvest_object, 'status')
        if status == 'delete':
            # Delete package
            context = {'model': model, 'session': model.Session,
                       'user': self._get_user_name(), 'ignore_auth': True}

            try:
                p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
                log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id,
                                                                    harvest_object.guid))
            except p.toolkit.ObjectNotFound:
                log.info('Package {0} already deleted.'.format(harvest_object.package_id))

            return True

        if harvest_object.content is None:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        try:
            dataset = json.loads(harvest_object.content)
        except ValueError:
            self._save_object_error('Could not parse content for object {0}'.format(harvest_object.id),
                                    harvest_object, 'Import')
            return False

        is_series = dataset.get('type') == 'dataset_series'

        def flag_current():
            # Get the last harvested object (if any)
            previous_objects = model.Session.query(HarvestObject) \
                                            .filter(HarvestObject.guid==harvest_object.guid) \
                                            .filter(HarvestObject.current==True)
            if is_series:
                # a series is not shared between sources: only the one of this source is replaced
                previous_objects = previous_objects.filter(
                    HarvestObject.harvest_source_id == harvest_object.harvest_source_id
                )
            previous_object = previous_objects.first()

            # Flag previous object as not current anymore
            if previous_object:
                previous_object.current = False
                previous_object.add()

            # Flag this object as the current one
            harvest_object.current = True
            harvest_object.add()

        flag_current()

        context = {
            'user': self._get_user_name(),
            'return_id_only': True,
            'ignore_auth': True,
        }

        dataset = self.modify_package_dict(dataset, {}, harvest_object)

        # Check if a dataset with the same guid exists. A series is looked up among the ones this
        # source imported: another source can have a series with the same URI.
        if is_series:
            existing_series = self._find_existing_series(harvest_object.guid, harvest_object.harvest_source_id)
            existing_dataset = (
                p.toolkit.get_action('package_show')({}, {'id': existing_series.id}) if existing_series else None
            )
        else:
            existing_dataset = self._get_existing_dataset(harvest_object.guid)

        import_warning = None

        def save_reference(defer_constraints=False):
            # Save reference to the package on the object
            harvest_object.package_id = dataset['id']
            harvest_object.add()

            if defer_constraints:
                # Defer constraints and flush so the dataset can be indexed with
                # the harvest object id (on the after_show hook from the harvester
                # plugin)
                model.Session.execute(
                    sa.text('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
                )
                model.Session.flush()

        def redo_bookkeeping(defer_constraints=False):
            # CKAN rolls back when validation fails: that undoes the flags and the reference too
            flag_current()
            save_reference(defer_constraints)

        try:
            package_plugin = lib_plugins.lookup_package_plugin(dataset.get('type', None))
            if existing_dataset:
                package_schema = package_plugin.update_package_schema()
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    package_schema = harvester.update_package_schema_for_update(package_schema)
                context['schema'] = package_schema

                # Don't change the dataset name even if the title has
                dataset['name'] = existing_dataset['name']
                dataset['id'] = existing_dataset['id']

                harvester_tmp_dict = {}

                # check if resources already exist based on their URI
                existing_resources =  existing_dataset.get('resources')
                resource_mapping = {r.get('uri'): r.get('id') for r in existing_resources if r.get('uri')}
                for resource in dataset.get('resources'):
                    res_uri = resource.get('uri')
                    if res_uri and res_uri in resource_mapping:
                        resource['id'] = resource_mapping[res_uri]

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    harvester.before_update(harvest_object, dataset, harvester_tmp_dict)

                try:
                    if dataset:
                        save_reference()

                        _, warning = call_dropping_invalid_values(
                            p.toolkit.get_action('package_update'), context, dataset, before_retry=redo_bookkeeping
                        )
                        import_warning = warning
                    else:
                        log.info('Ignoring dataset %s' % existing_dataset['name'])
                        return 'unchanged'
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Update validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    err = harvester.after_update(harvest_object, dataset, harvester_tmp_dict)

                    if err:
                        self._save_object_error('RDFHarvester plugin error: %s' % err, harvest_object, 'Import')
                        return False

                log.info('Updated dataset %s' % dataset['name'])

            else:
                package_schema = package_plugin.create_package_schema()
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    package_schema = harvester.update_package_schema_for_create(package_schema)
                context['schema'] = package_schema

                # We need to explicitly provide a package ID. A dataset series keeps the one it got
                # when it was gathered: the datasets of this harvest point at it.
                if not (is_series and dataset.get('id')):
                    dataset['id'] = str(uuid.uuid4())
                package_schema['id'] = [unicode_safe]

                harvester_tmp_dict = {}

                name = dataset['name']
                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    harvester.before_create(harvest_object, dataset, harvester_tmp_dict)

                try:
                    if dataset:
                        save_reference(defer_constraints=True)

                        _, warning = call_dropping_invalid_values(
                            p.toolkit.get_action('package_create'),
                            context,
                            dataset,
                            before_retry=lambda: redo_bookkeeping(defer_constraints=True)
                        )
                        import_warning = warning
                    else:
                        log.info('Ignoring dataset %s' % name)
                        return 'unchanged'
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Create validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

                for harvester in p.PluginImplementations(IDCATRDFHarvester):
                    err = harvester.after_create(harvest_object, dataset, harvester_tmp_dict)

                    if err:
                        self._save_object_error('RDFHarvester plugin error: %s' % err, harvest_object, 'Import')
                        return False

                log.info('Created dataset %s' % dataset['name'])

        except Exception as e:
            self._save_object_error('Error importing dataset %s: %r / %s' % (dataset.get('name', ''), e, traceback.format_exc()), harvest_object, 'Import')
            return False

        finally:
            model.Session.commit()

        if import_warning:
            self._save_object_error(import_warning, harvest_object, 'Import')

        return True

    def _find_existing_series(self, series_uri, source_id):
        '''
        The active dataset series that the given harvest source imported for the given RDF URI, or None.

        A series belongs to the source that created it. Two sources can define a series with the same
        URI, and each one gets its own, so it is found through this source's harvest objects and not
        through the 'guid' extra, which both of them carry.
        '''
        imported = model.Session.query(HarvestObject.package_id).\
            filter(HarvestObject.guid == str(series_uri)).\
            filter(HarvestObject.harvest_source_id == source_id).\
            filter(HarvestObject.package_id.isnot(None))

        return model.Session.query(model.Package).\
            filter(model.Package.id.in_(imported)).\
            filter(model.Package.type == 'dataset_series').\
            filter(model.Package.state == 'active').\
            first()

    def _parse_and_collect(
        self,
        items,
        source_dataset,
        harvest_job,
        guids_in_source,
        is_series=False,
        series_mapping=None
    ):
        # series_mapping, when given, is filled with the RDF URI -> id and name of each item
        object_ids = []
        label = "dataset series" if is_series else "dataset"

        for item in items:
            original_title = item.get("title", label)
            if not item.get("name"):
                item["name"] = self._gen_new_name(original_title)

            if item["name"] in self._names_taken:
                suffix = len([i for i in self._names_taken if i.startswith(item["name"] + "-")]) + 1
                item["name"] = f"{item['name']}-{suffix}"

            self._names_taken.append(item["name"])

            if not item.get("owner_org") and source_dataset.owner_org:
                item["owner_org"] = source_dataset.owner_org

            guid = self._get_guid(item, source_url=source_dataset.url)
            if not guid:
                self._save_gather_error(f"Could not get a unique identifier for {label}: {item}", harvest_job)
                continue

            item.setdefault("extras", []).append({"key": "guid", "value": guid})
            guids_in_source.append(guid)

            # Store the RDF URI -> id/name mapping before the object is saved, so a new series already
            # has its id when the datasets of this harvest point at it.
            if series_mapping is not None:
                series_uri = item.get("uri") or item.get("identifier")
                if series_uri:
                    # Try to find an existing active dataset series of this source
                    existing = self._find_existing_series(series_uri, harvest_job.source.id)

                    if existing:
                        item["name"] = existing.name
                    else:
                        item.setdefault("id", str(uuid.uuid4()))

                    series_mapping[str(series_uri)] = {
                        "id": existing.id if existing else item["id"],
                        "name": item["name"]
                    }

            obj = HarvestObject(guid=guid, job=harvest_job, content=json.dumps(item))
            obj.save()
            object_ids.append(obj.id)

        return object_ids
