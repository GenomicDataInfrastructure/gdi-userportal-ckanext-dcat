The `ckan dcat` command offers utilites to transform between DCAT RDF Serializations and CKAN datasets (`ckan dcat consume`) and
viceversa (`ckan dcat produce`). In both cases the input can be provided as a path to a file:

    ckan dcat consume -f ttl examples/dcat/dataset.ttl

    ckan dcat produce -f jsonld examples/ckan/ckan_dataset.json

or be read from stdin:

    ckan dcat consume -

The latter form allows chaininig commands for more complex metadata processing, e.g.:

    curl https://demo.ckan.org/api/action/package_search | jq .result.results | ckan dcat produce -f jsonld -

Both commands accept `-p/--profiles` with a space-separated list of RDF profiles. Without it they use
[`ckanext.dcat.rdf.profiles`](configuration.md#ckanextdcatrdfprofiles), and then the default profile.

`ckan dcat generate_static` writes a static JSON file of the datasets. It is deprecated and needs the
`dcat_json_interface` plugin.

For the full list of options check `ckan dcat consume --help` and `ckan dcat produce --help`.
