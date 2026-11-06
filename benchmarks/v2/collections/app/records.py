def only_mappings(items):
    from collections import Mapping
    return [dict(item) for item in items if isinstance(item, Mapping)]
