from fastapi.testclient import TestClient


def test_admin_root_serves_html(client: TestClient):
    """Verify GET /admin returns admin.html with proper elements."""
    res = client.get("/admin")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Admin Control Panel" in res.text
    assert 'id="modal-admin-login"' in res.text
    assert 'id="hero-status-badge"' in res.text
    assert 'id="btn-start-question"' in res.text
    assert 'id="btn-end-question"' in res.text
    assert 'id="modal-question-editor"' in res.text
    assert 'id="modal-leaderboard"' in res.text


def test_admin_static_css_and_js_served(client: TestClient):
    """Verify admin CSS and JS assets are served with 200 OK."""
    css_res = client.get("/css/admin.css")
    assert css_res.status_code == 200
    assert "--border-active" in css_res.text
    assert ".hero-control-card" in css_res.text

    js_res = client.get("/js/admin.js")
    assert js_res.status_code == 200
    assert "initAdmin" in js_res.text

    api_res = client.get("/js/admin-api.js")
    assert api_res.status_code == 200
    assert "adminApi" in api_res.text
