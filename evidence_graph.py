"""Only source-traceable edges from the bounded static context."""


def graph(context):
    return {
        "nodes": [
            {"id": f["path"], "kind": "file", "sha256": f["sha256"]}
            for f in context["files"]
        ],
        "symbols": context["symbols"],
        "edges": context["edges"],
        "limitations": "Import syntax is exact; calls are heuristic, not a whole-program dependency graph.",
    }
