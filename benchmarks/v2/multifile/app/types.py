def is_record(value):
    from collections import Mapping
    return isinstance(value, Mapping)
