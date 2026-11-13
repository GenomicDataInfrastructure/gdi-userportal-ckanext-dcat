## RDF DCAT harvester

The [RDF parser](writing-profiles.md#rdf-dcat-parser) is integrated into a harvester,
to allow automatic import of datasets from remote sources. To enable the RDF harvester, add the `harvest` and `dcat_rdf_harvester` plugins to your CKAN configuration file (you will also need to install [ckanext-harvest](https://github.com/ckan/ckanext-harvest)):

    ckan.plugins = ... harvest dcat_rdf_harvester

The harvester will download the remote file, extract all datasets using the parser and create or update actual CKAN datasets based on that.
It will also handle deletions, i.e. if a dataset is not present any more in the DCAT dump anymore it will get deleted from CKAN.

The harvester will look at the `content-type` HTTP header field to determine the used RDF format. Any format understood by the [RDFLib](https://rdflib.readthedocs.org/en/stable/plugin_parsers.html) library can be parsed. It is possible to override this functionality and provide a specific format using the harvester configuration. This is useful when the server does not return the correct `content-type` or when harvesting a file on the local file system without a proper extension. The harvester configuration is a JSON object that you fill into the harvester configuration form field.

    {"rdf_format":"text/turtle"}

### Profile of a harvest source

The RDF profiles a source is parsed with come from its config, in one of these ways:

* `metadata_profile`: the name of a metadata profile enabled in
  [`ckanext.dcat.metadata_profiles`](configuration.md#ckanextdcatmetadata_profiles). The profile's
  RDF profiles are used.
* `profile`: a space-separated chain of RDF profile names, an explicit override for a deployment
  without metadata profiles.

Setting both keys is an error. The harvester checks the keys when the source is saved and again
when it runs. A source with neither key uses the main metadata profile
([`ckanext.dcat.metadata_profiles.main`](configuration.md#ckanextdcatmetadata_profilesmain)), or
[`ckanext.dcat.rdf.profiles`](configuration.md#ckanextdcatrdfprofiles) when no metadata profiles
are configured.

    {"metadata_profile": "profile_a"}

### Maximum file size

The default max size of the file (for each HTTP response) to harvest is actually 50 MB. The size can be customised by setting the configuration option [`ckanext.dcat.max_file_size`](configuration.md#ckanextdcatmax_file_size) in your CKAN configuration file.

### Transitive harvesting

In transitive harvesting (i.e., when you harvest a catalog A, and a catalog X harvests your catalog), you may want to provide the original catalog info for each harvested dataset.

By setting the configuration option [`ckanext.dcat.expose_subcatalogs`](configuration.md#ckanextdcatexpose_subcatalogs) to true in your ini file, you'll enable the storing and publication of the source catalog for each harvested dataset.

The information contained in the harvested `dcat:Catalog` node will be stored as extras into the harvested datasets.
When serializing, your Catalog will expose the harvested Catalog using the `dct:hasPart` relation. This means that your catalog will have this structure:

- `dcat:Catalog` (represents your current catalog)
  - `dcat:dataset` (1..n, the dataset created within your catalog)
  - `dct:hasPart`
     - `dcat:Catalog` (info of one of the harvested catalogs)
        - `dcat:dataset` (dataset in the harvested catalog)
  - `dct:hasPart`
     - `dcat:Catalog` (info of one of another harvester catalog)
     ...


### Extending the RDF harvester

The DCAT RDF harvester has plugin hooks that allow to modify its behaviour from other extensions. These can be used by extensions implementing
the `IDCATRDFHarvester` interface. It provides the following methods:

* `before_download` and `after_download`: called just before and after retrieving the remote file, and can be used for instance to validate the contents.
* `update_session`: called before making the remote requests to update the `requests` session object, useful to add additional headers or for setting client certificates. Check the [`requests` documentation](http://docs.python-requests.org/en/master/user/advanced/#session-objects) for details.
* `before_create` / `after_create`: called before and after the `package_create` action has been performed
* `before_update` / `after_update`: called before and after the `package_update` action has been performed
* `after_parsing`: Called just after the content from the remote RDF file has been parsed

To know more about these methods, please check the source of [`ckanext-dcat/ckanext/dcat/interfaces.py`](https://github.com/ckan/ckanext-dcat/blob/master/ckanext/dcat/interfaces.py).

## JSON DCAT harvester (deprecated)

!!! Warning
    The DCAT JSON harvester is not maintained and will be removed in future versions

The DCAT JSON harvester supports importing JSON objects that are based on DCAT terms but are not defined as JSON-LD. The exact format for these JSON files
is the one described in the [spec.dataportals.org](http://spec.dataportals.org/#datasets-serialization-format) site. There are example files in the `examples/ckan` folder.

To enable the JSON harvester, add the `dcat_json_harvester` plugin to your CKAN configuration file:

    ckan.plugins = ... dcat_json_harvester
