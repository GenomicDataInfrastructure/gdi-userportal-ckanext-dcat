import pytest

from ckanext.dcat.schema_fields import is_multiple_text


@pytest.mark.parametrize(
    "field, expected",
    [
        (None, False),
        ({}, False),
        ({"field_name": "title"}, False),
        ({"field_name": "x", "validators": "ignore_missing unicode_safe"}, False),
        ({"field_name": "x", "preset": "multiple_text"}, True),
        ({"field_name": "x", "validators": "ignore_missing scheming_multiple_text"}, True),
        ({"field_name": "x", "validators": ["ignore_missing", "scheming_multiple_text"]}, True),
        ({"field_name": "x", "preset": "select"}, False),
    ],
)
def test_a_field_holds_a_list_of_texts_when_the_schema_says_so(field, expected):
    assert is_multiple_text(field) is expected
