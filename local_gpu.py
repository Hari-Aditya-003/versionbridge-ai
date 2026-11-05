"""Send one bounded chat request to an operator-managed Ollama SSH tunnel."""
import http.client
import json
import os

import gpu_guard

DEFAULT_MODEL = "qwen2.5-coder:1.5b-instruct-q4_K_M"


def complete(messages, replacements=(), arithmetic=False):
    gpu_guard.check()
    replacement = {"type": "string", "minLength": 1, "maxLength": 240}
    if replacements:
        replacement["enum"] = [line.strip() for line in replacements]
    if arithmetic and not replacements:
        replacement["pattern"] = r"^ *return [a-zA-Z0-9_+*() -]+$"
    schema = {
        "type": "object",
        "properties": {
            "diagnosis": {"type": "string", "minLength": 1, "maxLength": 360},
            "replacement": replacement,
        },
        "required": ["diagnosis", "replacement"],
        "additionalProperties": False,
    }
    model = os.getenv("VERSIONBRIDGE_LOCAL_MODEL", DEFAULT_MODEL)
    try:
        port = int(os.getenv("VERSIONBRIDGE_OLLAMA_PORT", "11434"))
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=70)
        body = json.dumps({
            "model": model, "messages": messages, "stream": False, "format": schema,
            "keep_alive": 0, "options": {
                "num_ctx": 2048, "num_predict": 320, "num_thread": 2, "temperature": 0,
            },
        })
        try:
            connection.request("POST", "/api/chat", body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError("Ollama rejected the request")
            result = json.loads(response.read(65536))
        finally:
            connection.close()
        answer = result["message"]["content"]
        if not isinstance(answer, str) or result.get("done") is not True:
            raise ValueError("Incomplete response")
        receipt = {"requested_model": model, "served_model": result.get("model"),
                   "provider": "Ollama", "accelerator": "unverified",
                   "tokens": {name: result[field] for name, field in (
                       ("prompt_tokens", "prompt_eval_count"), ("completion_tokens", "eval_count"),
                   ) if type(result.get(field)) is int}}
        return answer, receipt
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError, http.client.HTTPException) as exc:
        raise RuntimeError("Local inference failed. Check the Ollama model and SSH tunnel.") from exc
