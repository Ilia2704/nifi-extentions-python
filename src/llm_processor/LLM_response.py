from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship
from nifiapi.properties import PropertyDescriptor

import os
from pathlib import Path

try:
    import request
except ImportError:
    from llm_processor import request  # type: ignore


def _load_dotenv_once():
    for p in (Path.cwd() / ".env", Path.home() / ".env"):
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except Exception:
                pass
            break


def _prop_value(context, name: str, default: str = "") -> str:
    val = context.getProperty(name)
    if val is None:
        return default
    if hasattr(val, "getValue"):
        try:
            return (val.getValue() or default).strip()
        except Exception:
            pass
    if hasattr(val, "asString"):
        try:
            return (val.asString() or default).strip()
        except Exception:
            pass
    try:
        return (str(val) or default).strip()
    except Exception:
        return default


class LLM_response(FlowFileTransform):
    class Java:
        implements = ['org.apache.nifi.python.processor.FlowFileTransform']

    class ProcessorDetails:
        version = "0.3.4"  # ↑ bump для сброса кеша
        description = "Send entire FlowFile content to Gemini via request(prompt, api_key)."
        tags = ["LLM", "python", "google", "gemini", "transform"]

    # --- Ровно два свойства, без defaultValue/allowableValues ---
    _PD_API_KEY = PropertyDescriptor(
        name="api_key",
        description="Google Generative AI API key. If empty, uses env GOOGLE_AI_API_KEY.",
        required=False,
        sensitive=True,
    )
    _PD_SYSTEM_PROMPT = PropertyDescriptor(
        name="system_prompt",
        description="Optional system instruction (prefixed to user content).",
        required=False,
        sensitive=False,
    )

    def __init__(self, jvm=None, **kwargs):
        self.jvm = jvm
        try:
            super().__init__()
        except Exception:
            pass
        _load_dotenv_once()

    def getRelationships(self):
        return [
            Relationship(name="success", description="Processed successfully"),
            Relationship(name="failure", description="Processing failed"),
        ]

    def getPropertyDescriptors(self):
        return [self._PD_API_KEY, self._PD_SYSTEM_PROMPT]

    @staticmethod
    def _make_prompt(user_text: str, system_prompt: str) -> str:
        return f"{system_prompt.strip()}\n\n---\n{user_text}" if system_prompt else user_text

    @staticmethod
    def _get_api_key(context) -> str:
        prop_key = _prop_value(context, "api_key")
        if prop_key:
            return prop_key
        env_key = os.getenv("GOOGLE_AI_API_KEY", "").strip()
        if env_key:
            return env_key
        raise ValueError("API key missing: set processor property 'api_key' or env GOOGLE_AI_API_KEY.")

    def transform(self, context, flowfile):
        try:
            api_key = self._get_api_key(context)
            system_prompt = _prop_value(context, "system_prompt")

            data = flowfile.getContentsAsBytes() or b""
            user_text = data.decode("utf-8", errors="replace")
            prompt = self._make_prompt(user_text, system_prompt)

            model_text = request.request(prompt=prompt, api_key=api_key) or ""
            out_bytes = model_text.encode("utf-8")

            return FlowFileTransformResult(
                relationship="success",
                contents=out_bytes,
                attributes={
                    "llm.provider": "google",
                    "llm.client": "google.genai",
                    "llm.model": "gemini-2.5-flash",
                    "llm.format": "text",
                },
            )
        except Exception as e:
            return FlowFileTransformResult(
                relationship="failure",
                contents=None,
                attributes={
                    "error": (str(e) or "unknown error")[:512],
                    "llm.provider": "google",
                    "llm.client": "google.genai",
                },
            )
