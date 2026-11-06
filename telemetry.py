"""Read-only, cached host sensors. Cloud inference GPU telemetry is not exposed by the API."""

import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import threading
import time

_LOCK = threading.Lock()
_CACHE = None
_PREVIOUS = None


def percentage(used, total):
    return round(max(0, min(100, 100 * used / total)), 1) if total > 0 else None


def read_linux(proc=Path("/proc"), sys=Path("/sys"), previous=None):
    counters = list(map(int, (proc / "stat").read_text().splitlines()[0].split()[1:9]))
    total = sum(counters)
    idle = counters[3] + counters[4]
    cpu = None
    if previous and total > previous[0]:
        cpu = percentage(
            (total - previous[0]) - (idle - previous[1]), total - previous[0]
        )
    memory = {
        k: int(v)
        for k, v in re.findall(
            r"^(MemTotal|MemAvailable):\s*(\d+)", (proc / "meminfo").read_text(), re.M
        )
    }
    ram_total = memory.get("MemTotal", 0) * 1024
    used = max(0, ram_total - memory.get("MemAvailable", 0) * 1024)
    frequencies = re.findall(r"cpu MHz\s*:\s*([\d.]+)", (proc / "cpuinfo").read_text())
    speed = (
        round(sum(map(float, frequencies)) / len(frequencies)) if frequencies else None
    )
    temps = []
    for p in list((sys / "class/thermal").glob("thermal_zone*/temp"))[:16]:
        try:
            value = float(p.read_text()) / 1000
            if 0 < value < 130:
                temps.append(value)
        except (OSError, ValueError):
            pass
    return {
        "cpu": {
            "percent": cpu,
            "speed_mhz": speed,
            "temperature_c": max(temps) if temps else None,
        },
        "memory": {
            "total_bytes": ram_total,
            "used_bytes": used,
            "percent": percentage(used, ram_total),
        },
        "_counters": (total, idle),
    }


def _command(args):
    return subprocess.run(
        args, capture_output=True, text=True, timeout=1.5, check=True
    ).stdout


def read_mac():
    total = int(_command(["/usr/sbin/sysctl", "-n", "hw.memsize"]).strip())
    vm = _command(["/usr/bin/vm_stat"])
    page = int(re.search(r"page size of (\d+)", vm)[1])
    values = {k: int(v) for k, v in re.findall(r"^([^:\n]+):\s*(\d+)", vm, re.M)}
    available = (
        values.get("Pages free", 0)
        + values.get("Pages inactive", 0)
        + values.get("Pages speculative", 0)
    ) * page
    used = max(0, total - available)
    cpu_total = sum(
        float(n) for n in _command(["/bin/ps", "-A", "-o", "%cpu="]).split()
    )
    try:
        speed = (
            int(_command(["/usr/sbin/sysctl", "-n", "hw.cpufrequency"]).strip())
            / 1_000_000
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        speed = None
    return {
        "cpu": {
            "percent": min(100, round(cpu_total / (os.cpu_count() or 1), 1)),
            "speed_mhz": speed,
            "temperature_c": None,
            "basis": "process CPU estimates across logical cores",
        },
        "memory": {
            "total_bytes": total,
            "used_bytes": used,
            "percent": percentage(used, total),
            "basis": "total minus free, inactive and speculative pages",
        },
    }


def validate_gpu(record):
    names = [
        "timestamp",
        "memory_total_mb",
        "memory_used_mb",
        "utilization_percent",
        "temperature_c",
    ]
    values = {key: float(record[key]) for key in names}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError
    if (
        not 0 <= time.time() - values["timestamp"] <= 15
        or not 0 < values["memory_total_mb"] <= 1_000_000
        or not 0 <= values["memory_used_mb"] <= values["memory_total_mb"]
        or not 0 <= values["utilization_percent"] <= 100
        or not 0 <= values["temperature_c"] <= 130
    ):
        raise ValueError
    return {
        "available": True,
        **values,
        "memory_percent": percentage(
            values["memory_used_mb"], values["memory_total_mb"]
        ),
    }


def read_gpu_file(path):
    try:
        p = Path(path)
        if p.stat().st_size > 4096:
            raise ValueError
        return {
            **validate_gpu(json.loads(p.read_text())),
            "source": "trusted operator GPU monitor",
        }
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        return {
            "available": False,
            "reason": "GPU monitor is missing, stale, or invalid.",
        }


def local_gpu():
    if os.getenv("VERSIONBRIDGE_GPU_STATUS_FILE"):
        return read_gpu_file(os.environ["VERSIONBRIDGE_GPU_STATUS_FILE"])
    if not shutil.which("nvidia-smi"):
        return {"available": False, "reason": "No accessible NVIDIA sensor."}
    try:
        raw = _command(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ]
        )
        temp, used, total, util = map(float, raw.splitlines()[0].split(","))
        return {
            **validate_gpu(
                {
                    "timestamp": time.time(),
                    "temperature_c": temp,
                    "memory_used_mb": used,
                    "memory_total_mb": total,
                    "utilization_percent": util,
                }
            ),
            "source": "local nvidia-smi",
        }
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return {"available": False, "reason": "GPU sensor unavailable."}


def snapshot():
    global _CACHE, _PREVIOUS
    with _LOCK:
        if _CACHE and time.time() - _CACHE["sampled_at"] < 2:
            return _CACHE
        cloud = bool(os.getenv("SANDBOX_LOCATION", "").startswith("Vultr"))
        mode = (
            "local-gpu"
            if os.getenv("VERSIONBRIDGE_INFERENCE_MODE") == "local-gpu"
            else "vultr"
            if os.getenv("REQUIRE_INFERENCE") or os.getenv("VULTR_MODEL")
            else "sample"
        )
        try:
            host = (
                read_linux(previous=_PREVIOUS)
                if platform.system() == "Linux"
                else read_mac()
                if platform.system() == "Darwin"
                else {}
            )
            _PREVIOUS = host.pop("_counters", None)
            host["available"] = bool(host)
        except (OSError, ValueError, IndexError, KeyError, subprocess.SubprocessError):
            host = {"available": False, "reason": "Host sensors unavailable."}
        host["label"] = "Vultr application VM" if cloud else "Application host"
        gpu = local_gpu()
        inference = {
            "mode": mode,
            "label": "Private Ollama GPU"
            if mode == "local-gpu"
            else "Vultr Serverless Inference"
            if mode == "vultr"
            else "Sample proposals",
            "remote_gpu_metrics_available": False,
            "note": "Serverless inference GPU sensors are not exposed to this application."
            if mode == "vultr"
            else "GPU readings come from an accessible local sensor or a fresh trusted monitor.",
        }
        _CACHE = {
            "sampled_at": time.time(),
            "interval_seconds": 3,
            "host": host,
            "gpu": gpu,
            "inference": inference,
            "scope": "Whole application host, not browser/device or per-job attribution. Cloud inference runs separately.",
        }
        return _CACHE
