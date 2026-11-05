"""Collect Dell GPU telemetry through an existing operator SSH connection."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time


def monitor(target, output):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9@._-]{0,150}", target):
        raise ValueError("Invalid SSH target")
    while True:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target,
             "nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        values = result.stdout.splitlines()[0].split(",")
        if len(values) != 4:
            raise RuntimeError("Unexpected GPU telemetry")
        temperature, used, total, utilization = map(float, values)
        record = {"timestamp": time.time(), "temperature_c": temperature, "memory_used_mb": used,
                  "memory_total_mb": total, "utilization_percent": utilization}
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(record))
        temporary.replace(output)
        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ssh_target")
    parser.add_argument("--output", type=Path, default=Path("data/gpu-status.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    monitor(args.ssh_target, args.output)
