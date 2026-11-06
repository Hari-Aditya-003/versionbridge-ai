"""Version-pinned migration holdouts without permitted replacement enumerations."""

TASKS = {
    "v2-settings": {
        "title": "V2 · open-ended Pydantic settings migration",
        "fixture": "benchmarks/v2/settings",
        "allowed": ["app/config.py"],
        "versions": {"pydantic": "2.11.10", "python": "3.12.0"},
        "contract": "Preserve configuration defaults, field validation, and environment overrides.",
    },
    "v2-collections": {
        "title": "V2 · open-ended collections migration",
        "fixture": "benchmarks/v2/collections",
        "allowed": ["app/records.py"],
        "versions": {"python": "3.12.0"},
        "contract": "Select mappings and preserve all input keys and values; discard non-mappings.",
    },
    "v2-multifile": {
        "title": "V2 · two-file import migration",
        "fixture": "benchmarks/v2/multifile",
        "allowed": ["app/types.py", "app/service.py"],
        "versions": {"python": "3.12.0"},
        "contract": "Preserve mapping normalization and classification across both application modules.",
    },
}
