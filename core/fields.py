import json
from django.db import models


class JSONDataField(models.JSONField):
    """
    Custom JSON field that stores structured data (lists, dicts, etc.)
    as JSON. Extends Django's built-in JSONField with safe serialization
    handling for string inputs.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', list)
        kwargs.setdefault('blank', True)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        # Handle string values that may be JSON-encoded
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass
        return super().get_prep_value(value)
