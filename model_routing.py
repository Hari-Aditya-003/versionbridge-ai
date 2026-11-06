"""Opt-in, bounded sequential Vultr model selection for repair proposals.

This is model rotation across existing verification attempts, not a voting
ensemble, independent critic, or general multi-file repair engine.
"""
import re

_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}\Z")


def valid_model_id(value):
    return isinstance(value, str) and bool(_MODEL_ID.fullmatch(value))


def plan_models(mode, attempts, pool):
    """Return up to two independent provider model IDs, or () for legacy mode.

    `VULTR_MODEL_POOL` requires exactly two distinct comma-separated model IDs.
    The first handles attempt 1; the second handles attempt 2 only when the
    first candidate fails verification. No additional requests are issued when
    a patch passes on the first attempt.
    """
    if not pool:
        return ()
    if mode != "vultr":
        raise RuntimeError("VULTR_MODEL_POOL requires Vultr inference.")
    if type(attempts) is not int or attempts not in (1, 2):
        raise ValueError("Model routing supports one or two repair attempts.")
    if not isinstance(pool, str) or len(pool) > 255:
        raise ValueError("Invalid model pool.")
    models = [item.strip() for item in pool.split(",")]
    if len(models) != 2 or not all(valid_model_id(value) for value in models):
        raise ValueError("Configure exactly two valid Vultr model IDs.")
    if models[0] == models[1]:
        raise ValueError("Configure distinct model IDs for independent attempts.")
    return tuple(models[:attempts])
