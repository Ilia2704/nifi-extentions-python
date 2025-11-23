# demo_processor/swap.py
"""
Pure Python business logic for JsonKeyValueSwap processor.

This module does NOT depend on NiFi APIs. It only operates on Python
data structures (dict, list, primitives) and can be unit-tested separately.
"""

from typing import Any, Dict


def swap_top_level(obj: Any) -> Dict[str, str]:
    """
    Swap keys and values of a top-level JSON object.

    Input:
        obj  - parsed JSON value (expected to be a dict)

    Rules:
        - The top-level JSON value must be a dict (JSON object).
        - All keys must be strings (normal for JSON).
        - All values must be simple scalar types:
            str, int, float, bool, or None.
          If a value is a list or dict (or any other complex type),
          this function raises ValueError.
        - New keys are created from stringified values: new_key = str(value).
        - New values are the original keys.

        If multiple keys have the same value, the last one wins and
        overwrites the previous one (simple overwrite semantics).

    Returns:
        A new dict with swapped keys and values.

    Raises:
        ValueError if the input does not meet the rules above.
    """
    # Ensure that the top-level JSON value is an object
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON value must be an object (dict).")

    result: Dict[str, str] = {}

    for key, value in obj.items():
        # JSON object keys are usually strings, but we enforce this explicitly.
        if not isinstance(key, str):
            raise ValueError("All keys in the JSON object must be strings.")

        # Only scalar values are allowed for this simple demo.
        if not isinstance(value, (str, int, float, bool)) and value is not None:
            raise ValueError(
                f"Unsupported value type for key '{key}': {type(value).__name__}. "
                "Only scalar values (str, int, float, bool, None) are allowed."
            )

        # Turn the scalar value into a string to use as a new key.
        new_key = str(value)

        # If this new_key already exists in result, it will be overwritten.
        # This is acceptable for this simple demo processor.
        result[new_key] = key

    return result
