from fastapi.testclient import TestClient


def test_frontend_root_serves_html(client: TestClient):
    """Verify GET / returns index.html with appropriate title and screen containers."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Janmashtami Live Quiz" in res.text
    assert 'id="screen-registration"' in res.text
    assert 'id="screen-waiting"' in res.text
    assert 'id="screen-question"' in res.text
    assert 'id="screen-leaderboard"' in res.text
    assert 'id="connection-badge"' in res.text


def test_frontend_static_css_and_js_served(client: TestClient):
    """Verify static assets are served with 200 OK."""
    # CSS
    css_res = client.get("/css/style.css")
    assert css_res.status_code == 200
    assert "--primary-gold" in css_res.text
    assert ".option-btn" in css_res.text

    # JS Modules
    app_res = client.get("/js/app.js")
    assert app_res.status_code == 200
    assert "initApp" in app_res.text

    api_res = client.get("/js/api.js")
    assert api_res.status_code == 200
    assert "submitAnswer" in api_res.text

    ws_res = client.get("/js/websocket.js")
    assert ws_res.status_code == 200
    assert "QuizWebSocket" in ws_res.text

    state_res = client.get("/js/state.js")
    assert state_res.status_code == 200
    assert "AppState" in state_res.text
