"""One sequential primary/fallback pair; no fan-out or hidden extra attempts."""

import os
from model_registry import require_model


def plan(mode, categories, attempts=2, pool=""):
    if type(attempts) is not int or attempts not in (1, 2):
        raise ValueError("Choose one or two candidates.")
    provider = "ollama" if mode == "local-gpu" else "vultr"
    default = (
        os.getenv("VERSIONBRIDGE_LOCAL_MODEL", "qwen2.5-coder:1.5b-instruct-q4_K_M")
        if provider == "ollama"
        else os.getenv("VULTR_MODEL", "glm-5.3-flash")
    )
    models = [default, default]
    if pool:
        models = [item.strip() for item in pool.split(",")]
        if len(models) != 2 or models[0] == models[1]:
            raise ValueError("Configure exactly two distinct registered model IDs.")
    for model in models:
        require_model(provider, model)
    return [
        {
            "model": model,
            "provider": provider,
            "categories": list(categories),
            "reason": (
                "Evidence-backed baseline; no category holdout promotion yet."
                if i == 0
                else "Bounded retry only after policy or execution failure; previous feedback supplied."
            ),
            "attempt": i + 1,
        }
        for i, model in enumerate(models[:attempts])
    ]
