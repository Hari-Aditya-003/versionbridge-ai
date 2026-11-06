"""Untrusted behavior process. Its responses are data, never verdicts."""

from collections import UserDict
import json
import os
import sys
from types import MappingProxyType

if __name__ == "__main__":
    cases = json.loads(sys.stdin.read(65536))
    task = sys.argv[1]
    sys.path.insert(0, "/project")
    results = []
    if task == "v2-settings":
        from app.config import load_config

        for case in cases:
            os.environ["VB_SERVICE_NAME"] = case["name"]
            os.environ["VB_PORT"] = case["port"]
            try:
                results.append(load_config())
            except ValueError:
                results.append({"invalid": True})
    else:
        if task == "v2-collections":
            from app.records import only_mappings as transform
        elif task == "v2-multifile":
            from app.service import normalize as transform
        else:
            raise ValueError("Unknown behavior adapter")
        for case in cases:
            if case.get("classify"):
                from app.types import is_record

                results.append([is_record(UserDict({"x": 1})), is_record([("x", 1)])])
            elif case.get("empty"):
                results.append(transform([]))
            else:
                value = case["value"]
                results.append(
                    transform(
                        [
                            UserDict(value),
                            None,
                            MappingProxyType(value),
                            "text",
                            {},
                            [value],
                        ]
                    )
                )
    print(json.dumps(results))
