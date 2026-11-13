"""
Import a harvested dataset without the values CKAN rejects.

A remote catalogue can hold a value the metadata schema does not accept, for example a number of
records that is not an integer. Without this module CKAN rejects the whole dataset with a validation
error and the harvest object ends in an error. With it, the harvester imports the dataset without the
values that failed validation and reports each one as a warning on the harvest object.

Only a value is dropped, never the dataset: a dataset that still does not validate afterwards (a
missing title, an unknown organization) is reported with its original error.
"""

import copy
import logging

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

# A dataset without one of these cannot be stored, so an error on them is never worked around.
PROTECTED_KEYS = ("id", "name", "title", "owner_org", "type", "state")

# What the warning on the harvest object starts with.
WARNING_PREFIX = "Warning: imported without the invalid value"


def _is_message_list(errors):
    return isinstance(errors, (list, tuple)) and all(isinstance(item, str) for item in errors)


def without_invalid_values(value, errors, path=""):
    """
    Remove from ``value`` (a dict, edited in place) every value that ``errors`` (a CKAN error dict)
    names, and return one ``(path, dropped value, messages)`` tuple per removal.

    Errors on nested values are followed: a list of dicts (resources, repeating subfields) is matched by
    position. An error that names no value that can be removed (a missing field, a ``__junk`` key, a
    protected key) is left alone, so the caller still sees it when the dataset does not validate.
    """
    dropped = []
    if not isinstance(value, dict) or not isinstance(errors, dict):
        return dropped

    for key, key_errors in errors.items():
        if key.startswith("__") or key not in value:
            continue
        label = "%s.%s" % (path, key) if path else key

        if _is_message_list(key_errors):
            if not path and key in PROTECTED_KEYS:
                continue
            dropped.append((label, value.pop(key), list(key_errors)))
        elif isinstance(key_errors, (list, tuple)) and isinstance(value[key], list):
            for index, item_errors in enumerate(key_errors):
                if index < len(value[key]):
                    dropped += without_invalid_values(value[key][index], item_errors, "%s[%d]" % (label, index))
        elif isinstance(key_errors, dict) and isinstance(value[key], dict):
            dropped += without_invalid_values(value[key], key_errors, label)
    return dropped


def describe(dropped):
    """One line that names every dropped value, with the value and what CKAN said about it."""
    parts = ["%s = %r (%s)" % (label, value, "; ".join(messages)) for label, value, messages in dropped]
    return "%s: %s" % (WARNING_PREFIX, ", ".join(parts))


def call_dropping_invalid_values(action, context, dataset, before_retry=None):
    """
    Call a CKAN action (``package_create`` or ``package_update``) with ``dataset``. When it fails on
    validation, retry once without the values that failed.

    CKAN rolls the session back when validation fails, which also undoes what the harvester added
    before the call (the harvest object's package id). ``before_retry`` is called without arguments
    after the values are dropped and before the retry, to do that bookkeeping again.

    Returns ``(result, warning)``: the result of the action, and a line that names the dropped values
    (``None`` when nothing was dropped). ``dataset`` is changed in place to what was stored. A dataset
    that does not validate after the values are dropped raises the original ``ValidationError``.
    """
    try:
        return action(context.copy(), dataset), None
    except toolkit.ValidationError as error:
        cleaned = copy.deepcopy(dataset)
        dropped = without_invalid_values(cleaned, error.error_dict)
        if not dropped:
            raise

        retry_context = context.copy()
        retry_context.pop("__auth_audit", None)
        if before_retry:
            before_retry()
        try:
            result = action(retry_context, cleaned)
        except toolkit.ValidationError:
            raise error

    dataset.clear()
    dataset.update(cleaned)
    warning = describe(dropped)
    log.warning(warning)
    return result, warning
