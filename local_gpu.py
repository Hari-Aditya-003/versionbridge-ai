"""Send one bounded chat request to an operator-managed Ollama SSH tunnel."""
import http.client  # noqa: F401 - legacy transport mock surface.
import json
import os


DEFAULT_MODEL = "qwen2.5-coder:1.5b-instruct-q4_K_M"


def complete(messages, replacements=(), arithmetic=False):
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
    from providers.base import ModelRequest
    from providers.ollama import complete as complete_request
    model = os.getenv("VERSIONBRIDGE_LOCAL_MODEL", DEFAULT_MODEL)
    response = complete_request(ModelRequest("legacy-profile", model, messages, schema, 320))
    return json.dumps(response.candidate), {**response.receipt(), "accelerator": "unverified"}
