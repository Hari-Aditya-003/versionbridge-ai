def test_service_name():
    from app.config import load_config
    assert load_config()['service_name'] == 'bridge'
