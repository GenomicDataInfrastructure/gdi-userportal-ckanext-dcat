"""
A harvested dataset is imported without the values CKAN rejects, and the dropped values are reported.
"""

import pytest

import ckan.plugins.toolkit as toolkit

from ckanext.dcat.harvesters.invalid_values import (
    WARNING_PREFIX,
    call_dropping_invalid_values,
    describe,
    without_invalid_values,
)

INVALID_INTEGER = ["Invalid integer"]


class TestWithoutInvalidValues:
    def test_a_value_that_failed_is_removed_and_reported(self):
        dataset = {"title": "t", "number_of_records": "about 1000", "notes": "n"}

        dropped = without_invalid_values(dataset, {"number_of_records": INVALID_INTEGER})

        assert dataset == {"title": "t", "notes": "n"}
        assert dropped == [("number_of_records", "about 1000", INVALID_INTEGER)]

    def test_errors_on_resources_are_matched_by_position(self):
        dataset = {"resources": [{"name": "a", "size": "big"}, {"name": "b", "size": "7"}]}

        dropped = without_invalid_values(dataset, {"resources": [{"size": INVALID_INTEGER}, {}]})

        assert dataset["resources"] == [{"name": "a"}, {"name": "b", "size": "7"}]
        assert dropped == [("resources[0].size", "big", INVALID_INTEGER)]

    def test_errors_on_a_subfield_of_a_repeating_field_are_followed(self):
        dataset = {"contact": [{"name": "x", "email": "nope"}]}

        dropped = without_invalid_values(dataset, {"contact": [{"email": ["Invalid email"]}]})

        assert dataset == {"contact": [{"name": "x"}]}
        assert dropped[0][0] == "contact[0].email"

    @pytest.mark.parametrize("key", ["id", "name", "title", "owner_org", "type"])
    def test_a_protected_key_is_never_dropped(self, key):
        dataset = {key: "x"}

        assert without_invalid_values(dataset, {key: ["Invalid"]}) == []
        assert dataset == {key: "x"}

    def test_an_error_on_a_missing_value_or_a_junk_key_drops_nothing(self):
        dataset = {"title": "t"}

        assert without_invalid_values(dataset, {"notes_translated": ["Missing value"], "__junk": ["x"]}) == []
        assert dataset == {"title": "t"}

    def test_a_protected_name_is_only_protected_at_the_top_level(self):
        dataset = {"resources": [{"name": "a"}]}

        dropped = without_invalid_values(dataset, {"resources": [{"name": ["Invalid"]}]})

        assert dropped and dataset == {"resources": [{}]}


def test_the_warning_names_the_value_and_what_ckan_said():
    line = describe([("number_of_records", "about 1000", INVALID_INTEGER)])

    assert line == WARNING_PREFIX + ": number_of_records = 'about 1000' (Invalid integer)"


class Action:
    """Raises a validation error for every dataset that still holds a bad value."""

    def __init__(self, bad=("number_of_records",), extra_errors=None):
        self.bad = bad
        self.extra_errors = extra_errors or {}
        self.calls = []

    def __call__(self, context, dataset):
        self.calls.append((context, dict(dataset)))
        errors = {key: INVALID_INTEGER for key in self.bad if key in dataset}
        errors.update(self.extra_errors)
        if errors:
            raise toolkit.ValidationError(errors)
        return dataset["id"]


class TestCallDroppingInvalidValues:
    def test_a_valid_dataset_is_created_as_it_is(self):
        action = Action()
        dataset = {"id": "1", "title": "t"}

        result, warning = call_dropping_invalid_values(action, {"user": "u"}, dataset)

        assert (result, warning) == ("1", None) and dataset == {"id": "1", "title": "t"} and len(action.calls) == 1

    def test_a_dataset_with_an_invalid_value_is_imported_without_it_and_a_warning_is_returned(self):
        action = Action()
        dataset = {"id": "1", "title": "t", "number_of_records": "lots"}

        result, warning = call_dropping_invalid_values(action, {"user": "u"}, dataset)

        assert result == "1"
        assert dataset == {"id": "1", "title": "t"}  # what was stored
        assert "number_of_records = 'lots'" in warning and warning.startswith(WARNING_PREFIX)
        assert len(action.calls) == 2

    def test_the_original_error_is_raised_when_the_dataset_still_fails(self):
        action = Action(extra_errors={"notes_translated": ["Missing value"]})
        dataset = {"id": "1", "title": "t", "number_of_records": "lots"}

        with pytest.raises(toolkit.ValidationError) as raised:
            call_dropping_invalid_values(action, {}, dataset)

        assert "number_of_records" in raised.value.error_dict
        # the dataset is left as it was
        assert dataset == {"id": "1", "title": "t", "number_of_records": "lots"}

    def test_an_error_that_names_nothing_to_drop_is_raised_without_a_retry(self):
        action = Action(bad=(), extra_errors={"title": ["Missing value"]})

        with pytest.raises(toolkit.ValidationError):
            call_dropping_invalid_values(action, {}, {"id": "1"})

        assert len(action.calls) == 1

    def test_the_bookkeeping_is_redone_before_the_retry_only(self):
        steps = []
        action = Action()

        def action_with_log(context, dataset):
            steps.append("action")
            return action(context, dataset)

        call_dropping_invalid_values(
            action_with_log, {}, {"id": "1", "number_of_records": "x"}, before_retry=lambda: steps.append("bookkeeping")
        )

        assert steps == ["action", "bookkeeping", "action"]

    def test_the_context_of_the_caller_is_not_changed(self):
        context = {"user": "u", "__auth_audit": [1]}

        call_dropping_invalid_values(Action(), context, {"id": "1", "number_of_records": "x"})

        assert context == {"user": "u", "__auth_audit": [1]}
