# ckanext-dcat

[![Tests](https://github.com/ckan/ckanext-dcat/actions/workflows/test.yml/badge.svg)](https://github.com/ckan/ckanext-dcat/actions)

A [CKAN](https://github.com/ckan/ckan) extension that exposes and harvests dataset metadata as RDF using DCAT
and related vocabularies. It supports CKAN 2.10, 2.11 and 2.12.

## Documentation

The user guide is [docs/index.md](docs/index.md). It covers installation, configuration, endpoints,
profiles and the harvester. The site is built with mkdocs from `mkdocs.yml`.

## Installation

From a checkout, in the CKAN virtualenv:

    pip install -e .

Then enable the plugins as described in [Getting started](docs/getting-started.md).

## Running the tests

    pytest --ckan-ini=test.ini ckanext/dcat/tests

Some tests need ckanext-harvest, ckanext-scheming and ckanext-fluent installed.

## Releases

1. Choose the new version by semantic versioning.
2. Set it in `version` in `pyproject.toml`.
3. Add the release notes to `CHANGELOG.md` and create a GitHub release with them.

## Acknowledgements

Work on ckanext-dcat has been made possible in part by:

* the Government of Sweden and Vinnova, as part of work on [Öppnadata.se](http://oppnadata.se), the Swedish Open Data Portal.
* [FIWARE](https://www.fiware.org), a project funded by the European Commission to integrate different technologies to offer connected cloud services from a single platform.

If you can fund new developments or contribute please get in touch.

## Copying and License

This material is copyright (c) Open Knowledge.

It is open and licensed under the GNU Affero General Public License (AGPL) v3.0 whose full text may be found at:

http://www.fsf.org/licensing/licenses/agpl-3.0.html
