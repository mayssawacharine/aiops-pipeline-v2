from app.main import app

def test_health():
    client = app.test_client()
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'

def test_simulate_failed_build():
    client = app.test_client()
    res = client.get('/simulate?status=failed&duration=120&failed_tests=3')
    data = res.get_json()
    assert data['status'] == 'failed'
    assert data['duration_seconds'] == 120
    assert data['failed_tests'] == 3
