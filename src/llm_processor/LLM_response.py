from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.relationship import Relationship
from nifiapi.properties import PropertyDescriptor, StandardValidators  # ВАЖНО: объекты, не dict!

import os
from pathlib import Path

# твой модуль: request.request(prompt: str, api_key: str) -> str
try:
    import request
except ImportError:
    from llm_processor import request  # type: ignore


def _load_dotenv_once():
    """Ленивая подгрузка .env если есть (локально и на CI).
    Порядок поиска: CWD/.env, $HOME/.env. Не требует python-dotenv.
    """
    for p in (Path.cwd() / ".env", Path.home() / ".env"):
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k, v)
            except Exception:
                pass
            break


class LLM_response(FlowFileTransform):
    """
    Отправляет содержимое FlowFile в LLM (через ваш модуль `request`) и пишет ответ в тело.

    Свойства:
      - api_key: (опц.) API ключ; если пусто — возьмём из окружения GOOGLE_AI_API_KEY и/или .env
      - system_prompt: (опц.) системная инструкция (добавляется префиксом к prompt)
      - response_format: (опц.) 'text' | 'json' (по умолчанию 'text')
    """

    class Java:
        implements = ['org.apache.nifi.python.processor.FlowFileTransform']

    class ProcessorDetails:
        version = "0.3.1"
        description = "Calls your `request(prompt, api_key)` (Gemini) with entire FlowFile content."
        tags = ["LLM", "python", "transform", "google", "gemini", "generative ai"]

    # --- PropertyDescriptors (возвращаем объекты, не dict!) ---
    _PD_API_KEY = PropertyDescriptor(
        name="api_key",
        displayName="Google API Key",
        description="API ключ Google Generative AI. Если пусто — будет использован env GOOGLE_AI_API_KEY/.env",
        required=False,                  # делаем опциональным: есть фолбэк из env
        sensitive=True,
        additonalDetails="",             # поле может отсутствовать в твоей версии API — безопасно убрать
        validators=[StandardValidators.NON_EMPTY_VALIDATOR]  # валидатор сработает только если поле заполнено
    )

    _PD_SYSTEM_PROMPT = PropertyDescriptor(
        name="system_prompt",
        displayName="System Prompt",
        description="Системная инструкция (будет префиксом к пользовательскому запросу).",
        required=False,
        sensitive=False
    )

    _PD_RESPONSE_FORMAT = PropertyDescriptor(
        name="response_format",
        displayName="Response Format",
        description="Формат ответа, который записывается в FlowFile: 'text' или 'json'.",
        required=False,
        allowableValues=["text", "json"],
        defaultValue="text"
    )

    def __init__(self, jvm=None, **kwargs):
        self.jvm = jvm
        try:
            super().__init__()
        except Exception:
            pass
        # однократно подгружаем .env (чтобы локально/на CI было прозрачно)
        _load_dotenv_once()

    def getRelationships(self):
        return [
            Relationship(name="success", description="Processed successfully"),
            Relationship(name="failure", description="Processing failed"),
        ]

    def getPropertyDescriptors(self):
        # ВАЖНО: список из PropertyDescriptor
        return [self._PD_API_KEY, self._PD_SYSTEM_PROMPT, self._PD_RESPONSE_FORMAT]

    @staticmethod
    def _make_prompt(user_text: str, system_prompt: str) -> str:
        if system_prompt:
            return f"{system_prompt.strip()}\n\n---\n{user_text}"
        return user_text

    @staticmethod
    def _get_api_key(context) -> str:
        # 1) Берём из свойства, если задано
        prop_key = (context.getProperty("api_key") or "").strip()
        if prop_key:
            return prop_key
        # 2) Из окружения (включая .env, уже подгружен)
        env_key = os.getenv("GOOGLE_AI_API_KEY", "").strip()
        if env_key:
            return env_key
        raise ValueError(
            "API key is missing. Set processor property 'api_key' "
            "or provide environment variable GOOGLE_AI_API_KEY (optionally via .env)."
        )

    def transform(self, context, flowfile):
        try:
            api_key = self._get_api_key(context)
            system_prompt = (context.getProperty("system_prompt") or "").strip()
            response_format = (context.getProperty("response_format") or "text").strip().lower()
            if response_format not in ("text", "json"):
                response_format = "text"

            data_bytes = flowfile.getContentsAsBytes() or b""
            user_text = data_bytes.decode("utf-8", errors="replace")
            prompt = self._make_prompt(user_text, system_prompt)

            model_text = request.request(prompt=prompt, api_key=api_key) or ""

            if response_format == "json":
                import json as _json
                out_bytes = _json.dumps({"text": model_text}, ensure_ascii=False).encode("utf-8")
                fmt = "json"
            else:
                out_bytes = model_text.encode("utf-8")
                fmt = "text"

            return FlowFileTransformResult(
                relationship="success",
                contents=out_bytes,
                attributes={
                    "llm.provider": "google",
                    "llm.client": "google.genai",
                    "llm.format": fmt,
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
