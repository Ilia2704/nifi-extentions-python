"""
Simple LLM HTTP client used by LLMRequestProcessor.
"""

import json
import requests


def call_llm(host: str, 
             port: str, 
             system_prompt: str, 
             temperature: float, 
             user_request: str) -> str:
    """
    Call an external LLM endpoint that accepts POST /generate with JSON.

    Current expected format on the server side (minimal):
        {
            "prompt": "<text>",
            "max_new_tokens": 100
        }

    This client:
      - prepends system_prompt to user_text inside the "prompt" field;
      - also sends "system_prompt" and "temperature" as separate fields
        so the server can start using them later.
    """

    url = f"http://{host}:{port}/generate"

    payload = {
        # What your server already expects:
        "prompt": user_request,
        "max_new_tokens": 100,
        # Fields for future use on the server side:
        "system_prompt": system_prompt,
        "temperature": float(temperature),
    }

    # Send HTTP POST to the LLM server
    resp = requests.post(url, 
                         json=payload, 
                         timeout=30.0)
    resp.raise_for_status()

    data = resp.json()

    # Try several common response formats
    if isinstance(data, dict):
        if "response" in data:
            return str(data["response"])
        if "generated_text" in data:
            return str(data["generated_text"])
        if "results" in data and isinstance(data["results"], list) and data["results"]:
            first = data["results"][0]
            if isinstance(first, dict) and "text" in first:
                return str(first["text"])

    # Fallback: return whole JSON as string
    return json.dumps(data, ensure_ascii=False)
