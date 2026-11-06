def normalize(rows):
    from collections import Mapping
    from app.types import is_record
    return [dict(row) for row in rows if isinstance(row, Mapping) and is_record(row)]
