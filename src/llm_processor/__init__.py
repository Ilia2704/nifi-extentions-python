"""
NiFi Python processor: sends FlowFile content to an external LLM endpoint.

All NiFi-related classes live here.
LLM HTTP logic is in llm_client.py.
"""

from typing import Any

from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship

# Simple import: NiFi loads llm_client.py as top-level module "llm_client"
from llm_client import call_llm


class LLMRequestProcessor(FlowFileTransform):
    """
    Processor that:
      - reads FlowFile content as UTF-8 text,
      - sends it to an external LLM endpoint,
      - replaces content with the LLM response.
    """

    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        version = "0.1.1"
        description = (
            "Sends FlowFile text to an external LLM endpoint using HOST, PORT, "
            "system prompt (Russian) and temperature."
        )
        tags = ["llm", "ai", "http", "demo"]
        # 'requests' is used in llm_client.py; here it's just documentation
        dependencies = ["requests"]

    def __init__(self, jvm=None, **kwargs: Any) -> None:
        """
        Proper constructor for NiFi FlowFileTransform processors.

        NiFi instantiates processors as ProcessorClass(jvm=gateway.jvm).
        We must NOT forward 'jvm' or **kwargs to FlowFileTransform.__init__().
        """
        self.jvm = jvm
        try:
            super().__init__()
        except Exception:
            pass

    def getPropertyDescriptors(self):
        """
        Define processor properties:
          - HOST: LLM host
          - PORT: LLM port
          - System Prompt: Russian system prompt
          - Temperature: sampling temperature
        """
        from nifiapi.properties import PropertyDescriptor

        return [
            PropertyDescriptor(
                name="HOST",
                description="Hostname of the LLM instance (e.g. 127.0.0.1).",
                required=True,
                sensitive=False,
            ),
            PropertyDescriptor(
                name="PORT",
                description="Port of the LLM instance (e.g. 8000).",
                required=True,
                sensitive=False,
            ),
            PropertyDescriptor(
                name="System Prompt",
                description="System prompt text in Russian.",
                required=False,
                sensitive=False,
            ),
            PropertyDescriptor(
                name="Temperature",
                description="Sampling temperature (float, e.g. 0.7).",
                required=False,
                sensitive=False,
            ),
        ]

    def transform(self, context, flowfile) -> FlowFileTransformResult:
        """
        Main method called by NiFi for each FlowFile.

        - Reads text from FlowFile.
        - Reads HOST, PORT, System Prompt, Temperature from properties.
        - Calls external LLM via call_llm().
        - On success: replaces content with LLM response, routes to 'success'.
        - On error: keeps original content, routes to 'failure'.
        """
        # Read content as bytes and decode as UTF-8
        data = flowfile.getContentsAsBytes() or b""
        user_text = data.decode("utf-8")

        # Read properties
        host = context.getProperty("HOST")
        port = context.getProperty("PORT")

        system_prompt = context.getProperty("System Prompt") or ""
        temperature_str = context.getProperty("Temperature") or "0.7"

        try:
            temperature = float(temperature_str)
        except ValueError:
            temperature = 0.7

        try:
            # Call external LLM
            result_text = call_llm(
                host=host,
                port=port,
                system_prompt=system_prompt,
                temperature=temperature,
                user_text=user_text,
            )

            # Successful result: new content + simple flag attribute
            return FlowFileTransformResult(
                relationship="success",
                contents=result_text,
                attributes={
                    "llm.success": "true",
                },
            )

        except Exception as e:
            # Any error: route to failure, keep original content
            return FlowFileTransformResult(
                relationship="failure",
                contents=None,
                attributes={
                    "llm.success": "false",
                    "llm.error": str(e)[:512],
                },
            )
    
    def getRelationships(self):
        """
        Explicitly declare processor relationships for tests and NiFi.

        We define:
          - success : JSON processed and swapped
          - failure : any error during decode/parse/swap
        """
        return [
            Relationship(
                name="success",
                description="JSON successfully swapped (keys <-> values)"
            ),
            Relationship(
                name="failure",
                description="Error while processing JSON; original content kept"
            ),
        ]
