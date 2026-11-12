"""
What a scheming field says about itself, read the same way everywhere in the RDF profiles.

The profiles know the RDF side of a property (its predicate, its class, its vocabulary). Whether the CKAN
field holds a list of texts is the schema's to say: a profile asks here instead of repeating a check on the
validators.

Standard library only; the function takes a field of the loaded schema as a mapping.
"""
from typing import Mapping, Optional

MULTIPLE_TEXT_PRESET = "multiple_text"
MULTIPLE_TEXT_VALIDATOR = "scheming_multiple_text"


def is_multiple_text(field: Optional[Mapping]) -> bool:
    """Whether a field holds a list of texts (``preset: multiple_text`` or the ``scheming_multiple_text`` validator).

    A field that is not in the schema holds one value, so None gives False.
    """
    if not field:
        return False
    return field.get("preset") == MULTIPLE_TEXT_PRESET or MULTIPLE_TEXT_VALIDATOR in str(field.get("validators", ""))
