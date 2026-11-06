def test_normalize():
    from app.service import normalize
    assert normalize([{'id': 2}, None]) == [{'id': 2}]
