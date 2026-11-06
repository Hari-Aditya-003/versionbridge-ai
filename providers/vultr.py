"""Vultr structured JSON transport; failed requests keep their reservation."""

import json
import os
import time
from urllib.request import Request, urlopen
import budget
from providers.base import ModelResponse, ProviderError


def complete(request, *, opener=None):
    key = os.getenv("VULTR_API_KEY")
    if not key:
        raise ProviderError(
            "configuration", "Configure Vultr inference in the worker environment."
        )
    body = {
        "model": request.model,
        "max_tokens": request.max_tokens,
        "messages": request.messages,
        "reasoning_effort": "minimal",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "repair_proposal",
                "strict": True,
                "schema": request.schema,
            },
        },
    }
    encoded = json.dumps(body).encode()
    allowance = budget.reserve(len(encoded), request.max_tokens)
    http = Request(
        "https://api.vultrinference.com/v1/chat/completions",
        encoded,
        {"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with (opener or urlopen)(http, timeout=30) as response:
            result = json.loads(response.read(524288))
        answer = result["choices"][0]["message"]["content"]
        candidate = json.loads(
            answer.strip().removeprefix("```json").removesuffix("```").strip()
        )
        if not isinstance(candidate, dict):
            raise ValueError
        usage = result.get("usage", {})
        tokens = {
            k: usage[k]
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            if isinstance(usage, dict) and type(usage.get(k)) is int and usage[k] >= 0
        }
        return ModelResponse(
            "Vultr Serverless Inference",
            request.model,
            result.get("model"),
            result.get("id"),
            tokens,
            (time.monotonic() - started) * 1000,
            candidate,
            allowance,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        RecursionError,
    ) as exc:
        error = ProviderError(
            "transport_or_schema",
            "Vultr did not return a complete structured proposal.",
        )
        error.reservation = allowance
        raise error from exc
