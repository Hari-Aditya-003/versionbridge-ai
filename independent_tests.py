"""Trusted supervisor compares behavior; application code runs only in a child."""

import ctypes
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

COUNTS = {"v2-settings": 4, "v2-collections": 101, "v2-multifile": 102}


def requests_for(task):
    randomizer = random.Random(7319)
    if task == "v2-settings":
        cases = [
            {"name": name, "port": port}
            for name, port in [
                ("worker", "9101"),
                ("bridge-prod", "6553"),
                ("x", "0"),
                ("x", "not-an-int"),
            ]
        ]
        expected = [
            {"service_name": c["name"], "port": int(c["port"])} for c in cases[:-1]
        ] + [{"invalid": True}]
    else:
        cases = [
            {
                "value": {
                    "id": randomizer.randint(-10000, 10000),
                    "label": str(randomizer.randint(0, 20)),
                }
            }
            for _ in range(100)
        ] + [{"empty": True}]
        expected = [
            [c["value"], c["value"], {}] if not c.get("empty") else [] for c in cases
        ]
        if task == "v2-multifile":
            cases.append({"classify": True})
            expected.append([True, False])
    return cases, expected


def check(task):
    if task not in COUNTS:
        raise ValueError("Unsupported independent suite")
    # Prevent source running as the same UID from opening the supervisor's
    # /proc memory or output descriptors. Application code is never imported here.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(4, 0, 0, 0, 0) != 0:
        raise RuntimeError("Cannot protect supervisor process")
    cases, expected = requests_for(task)
    worker = Path(__file__).with_name("independent_worker.py")
    child = subprocess.run(
        [sys.executable, "-I", str(worker), task],
        input=json.dumps(cases),
        text=True,
        capture_output=True,
        timeout=12,
        check=True,
    )
    if len(child.stdout) > 65536:
        raise ValueError("Oversized behavior response")
    actual = json.loads(child.stdout)
    if not isinstance(actual, list) or actual != expected:
        raise AssertionError("Independent behavioral comparison failed")
    return len(cases)


if __name__ == "__main__":
    task = sys.argv[1]
    count = check(task)
    print(
        json.dumps(
            {
                "passed": True,
                "checks": count,
                "seed": 7319,
                "suite": task,
                "protocol": "behavior-supervisor-v2",
                "provenance": "read-only supervisor; source executed only in isolated child",
                "suite_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            }
        )
    )
