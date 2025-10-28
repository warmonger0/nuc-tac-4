"""
Constants module for the Natural Language SQL Interface.

This module contains configuration constants used throughout the application,
including delimiter conventions for flattening nested JSON structures.

Delimiter Conventions:
- NESTED_FIELD_DELIMITER: Separates nested object paths (e.g., "address__city")
- ARRAY_INDEX_DELIMITER: Prefix for array item indexing (e.g., "items_0", "items_1")

The double underscore (__) is chosen for nested fields because it's uncommon in
typical field names and clearly indicates nesting hierarchy. The underscore (_)
followed by a number is used for array indices to maintain consistency with
common naming conventions.
"""

# Delimiter used to separate nested object paths when flattening
# Example: {"user": {"name": "John"}} -> "user__name": "John"
NESTED_FIELD_DELIMITER = "__"

# Delimiter used as prefix for array item indexing
# Example: {"tags": ["a", "b"]} -> "tags_0": "a", "tags_1": "b"
ARRAY_INDEX_DELIMITER = "_"
