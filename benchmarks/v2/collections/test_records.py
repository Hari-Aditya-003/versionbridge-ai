def test_mappings():
    from app.records import only_mappings
    assert only_mappings([{'id': 1}, 'ignore']) == [{'id': 1}]
