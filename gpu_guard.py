"""Validate trusted GPU telemetry before an optional local inference request."""
import json
import math
import os
from pathlib import Path
import time


def check():
    filename = os.getenv("VERSIONBRIDGE_GPU_STATUS_FILE")
    if not filename:
        return
    try:
        telemetry = json.loads(Path(filename).read_text())
        for field in ("timestamp", "memory_total_mb", "memory_used_mb", "temperature_c", "utilization_percent"):
            if not math.isfinite(float(telemetry[field])):
                raise ValueError("Invalid GPU telemetry")
        age = time.time() - float(telemetry["timestamp"])
        free_mb = float(telemetry["memory_total_mb"]) - float(telemetry["memory_used_mb"])
        if not 0 <= age <= 15:
            raise ValueError("GPU telemetry is stale")
        if float(telemetry["temperature_c"]) >= 65:
            raise ValueError("GPU temperature reached the quiet-mode limit")
        if float(telemetry["utilization_percent"]) >= 30:
            raise ValueError("GPU is busy with another workload")
        if free_mb < 1536:
            raise ValueError("GPU has insufficient free memory for quiet mode")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Local inference paused by GPU quiet mode. " + str(exc)) from exc
