"""Trusted independent checks baked into the read-only runtime, never sent to the model."""

from collections import UserDict
import json
import os
from pathlib import Path
import random
import sys
from types import MappingProxyType


def check(task):
    sys.path.insert(0, "/project")
    random.seed(7319)
    count = 0
    if task == "v2-settings":
        from app.config import load_config

        for name, port in [("worker", 9101), ("bridge-prod", 6553), ("x", 0)]:
            os.environ["VB_SERVICE_NAME"] = name
            os.environ["VB_PORT"] = str(port)
            assert load_config() == {"service_name": name, "port": port}
            count += 1
        os.environ["VB_PORT"] = "not-an-int"
        try:
            load_config()
        except ValueError:
            count += 1
        else:
            raise AssertionError("Invalid port must be rejected")
    elif task in ("v2-collections", "v2-multifile"):
        if task == "v2-collections":
            from app.records import only_mappings as transform
        else:
            from app.service import normalize as transform
            from app.types import is_record

            assert is_record(UserDict({"x": 1})) and not is_record([("x", 1)])
            count += 1
        for _ in range(100):
            value = {
                "id": random.randint(-10000, 10000),
                "label": str(random.randint(0, 20)),
            }
            inputs = [
                UserDict(value),
                None,
                MappingProxyType(value),
                "text",
                {},
                [value],
            ]
            assert transform(inputs) == [value, value, {}]
            count += 1
        assert transform([]) == []
        count += 1
    else:
        raise ValueError("Unsupported trusted independent suite")
    return count


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
                "provenance": "read-only image /opt/versionbridge/independent_tests.py",
                "suite_sha256": __import__("hashlib")
                .sha256(Path(__file__).read_bytes())
                .hexdigest(),
            }
        )
    )
