# demo_processor/__init__.py
"""
Demo NiFi Python processor package.

This module contains the JsonKeyValueSwap processor class which demonstrates
how to implement a simple FlowFileTransform in Python.
"""

import json
from typing import Any, Dict

from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship  # imported for symmetry/demo, not used directly

# Import pure business logic from the local module
from swap import swap_top_level


class JsonKeyValueSwap(FlowFileTransform):
    """
    Demo processor: swap keys and values of a top-level JSON object.

    Example:
        Input content:  {"a": 1, "b": 2, "c": 1}
        Output content: {"1": "c", "2": "b"}

    Only simple scalar values are allowed (str, int, float, bool, None).
    If the JSON is not an object or contains complex values (list/dict),
    the FlowFile is routed to 'failure'.
    """

    # This inner class tells NiFi which Java interface this Python class implements.
    class Java:
        # This exact string comes from NiFi Python Developer Guide.
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    # Metadata that NiFi shows in the UI for this processor.
    class ProcessorDetails:
        # Version of this processor implementation.
        version = "0.1.2"

        # Short human-readable description.
        description = (
            "Demo processor that swaps keys and values of a top-level JSON object. "
            "Values become new keys (stringified), keys become new values. "
            "Only simple scalar values are supported."
        )

        # List of tags to help find this processor in NiFi UI.
        tags = ["demo", "json", "swap", "python"]

        # Optional: list of PyPI dependencies (empty for this simple demo).
        dependencies = []

    def __init__(self, jvm=None, **kwargs):
        """
        Proper constructor for NiFi Python FlowFileTransform processors.

        NiFi always instantiates processors as:
            ProcessorClass(jvm=gateway.jvm)

        The base FlowFileTransform.__init__ does NOT accept arguments,
        so we must not pass 'jvm' or **kwargs to super().
        """

        # Store JVM reference if needed
        self.jvm = jvm

        # Call base constructor without arguments for compatibility
        try:
            super().__init__()
        except TypeError:
            pass
        except Exception:
            pass


    # We do NOT override getPropertyDescriptors() or getRelationships()
    # for this demo. In that case NiFi uses default relationships for
    # FlowFileTransform:
    #   - success
    #   - failure
    #   - original

    def transform(self, context, flowfile) -> FlowFileTransformResult:
        """
        Main method called by NiFi for each FlowFile.

        - Reads FlowFile content as UTF-8 JSON.
        - Swaps keys and values using swap_top_level().
        - On success: returns new JSON content, routes to 'success'.
        - On error: keeps original content, routes to 'failure' and sets
          an 'json.swap.error' attribute.
        """
        # Read original content as bytes (can be empty)
        data: bytes = flowfile.getContentsAsBytes() or b""

        try:
            # Decode content as UTF-8 text
            text: str = data.decode("utf-8")

            # Parse text as JSON
            obj: Any = json.loads(text)

            # Apply pure business logic (defined in swap.py)
            swapped: Dict[str, str] = swap_top_level(obj)

            # Serialize swapped object back to JSON text
            swapped_text: str = json.dumps(
                swapped,
                ensure_ascii=False,      # keep non-ASCII chars readable
                separators=(",", ":"),   # compact JSON without extra spaces
            )

            # Build a few simple attributes for demonstration
            attrs: Dict[str, str] = {
                "json.swap": "true",                       # processor succeeded
                "json.swap.original.size": str(len(obj)),  # number of keys before
                "json.swap.result.size": str(len(swapped)) # number of keys after
            }

            # Return a successful result:
            # - relationship='success' to route to success
            # - contents=swapped_text to replace FlowFile content
            # - attributes=attrs to add new attributes
            return FlowFileTransformResult(
                relationship="success",
                contents=swapped_text,
                attributes=attrs,
            )

        except Exception as e:
            # Any error (decode / JSON parse / swap logic) ends up here.
            # According to NiFi docs, 'failure' is a standard relationship
            # for FlowFileTransform processors.

            error_message = str(e)[:512]  # keep attribute reasonably short

            # We do not change the content on failure: contents=None means
            # NiFi will keep the original FlowFile content.
            return FlowFileTransformResult(
                relationship="failure",
                contents=None,
                attributes={
                    "json.swap": "false",
                    "json.swap.error": error_message,
                },
            )
