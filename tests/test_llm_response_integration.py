# tests/test_llm_response_integration.py
import os
import importlib
import pytest

def _have_key():
    return bool(os.getenv("GOOGLE_AI_API_KEY", "").strip())

@pytest.mark.integration
def test_transform_real_request():
    if not _have_key():
        pytest.skip("GOOGLE_AI_API_KEY is not set; skipping real request test")

    # импортируем процессор
    mod = importlib.import_module("llm_processor.LLM_response")
    LLM_response = mod.LLM_response

    # заглушки контекста и flowfile — без подмен запроса!
    class DummyContext:
        def __init__(self, props=None):
            self.props = props or {}
        def getProperty(self, name: str):
            return self.props.get(name)

    class DummyFlowFile:
        def __init__(self, body: bytes):
            self._body = body
        def getContentsAsBytes(self) -> bytes:
            return self._body

    # небольшой промпт, чтобы ответ пришёл быстро и дёшево
    flowfile = DummyFlowFile(b"Say just one short sentence about the sky.")
    context = DummyContext({
        # ключ берём из окружения: свойство api_key намеренно не задаём
        "system_prompt": "You are concise.",
        "response_format": "text",
    })

    proc = LLM_response()
    result = proc.transform(context, flowfile)

    # если процессор вернул failure — покажем ошибку целиком
    if result.relationship != "success":
        err = (result.attributes or {}).get("error", "<no error>")
        pytest.fail(f"Processor failed: {err}")

    # базовые проверки полезности ответа
    assert result.contents, "Empty response body"
    text = result.contents.decode("utf-8", errors="replace").strip()
    assert len(text) > 0, "Model returned empty text"
    assert len(text) < 2000, "Response looks unexpectedly large"
    # Очень мягкая проверка, что это короткое предложение
    assert "." in text or "!" in text, f"Unexpected response content: {text!r}"

    # метаданные
    assert result.attributes.get("llm.provider") == "google"
    assert result.attributes.get("llm.client") == "google.genai"
    assert result.attributes.get("llm.format") == "text"
