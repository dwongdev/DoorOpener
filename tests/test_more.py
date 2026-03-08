from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


def client_app():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _headers():
    return {
        "User-Agent": "pytest-client/2.0 (+https://example.test)",
        "Accept-Language": "en-US",
        "Content-Type": "application/json",
    }


def test_login_redirects_to_admin_when_oidc_disabled():
    c = client_app()
    r = c.get("/login", follow_redirects=False)
    # When oauth is not registered, login should take us to admin
    assert r.status_code in (302, 303)
    assert "/admin" in r.headers.get("Location", "")


def test_oidc_callback_invalid_audience(monkeypatch):
    # Provide oauth object and token with wrong audience
    import app as app_module

    class _DummyOAuth:
        class _Auth:
            def authorize_access_token(self):
                return {
                    "id_token": "dummy",
                    "userinfo": {
                        "aud": "someone-else",
                        "iss": "https://auth.example.com",
                        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
                        "nonce": "abc",
                        "email": "alice@example.com",
                        "groups": ["dooropener-users"],
                    },
                }

        authentik = _Auth()

    app_module.oauth = _DummyOAuth()
    app_module.oidc_client_id = "dooropener-client"
    app_module.oidc_issuer = "https://auth.example.com"

    c = client_app()
    with c.session_transaction() as s:
        s["oidc_state"] = "expected"
        s["oidc_nonce"] = "abc"
    r = c.get("/oidc/callback?state=expected", follow_redirects=False)
    assert r.status_code == 401


def test_oidc_callback_invalid_issuer(monkeypatch):
    import app as app_module

    class _DummyOAuth:
        class _Auth:
            def authorize_access_token(self):
                return {
                    "id_token": "dummy",
                    "userinfo": {
                        "aud": "dooropener-client",
                        "iss": "https://bad-issuer.example.com",
                        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
                        "nonce": "abc",
                        "email": "bob@example.com",
                        "groups": ["dooropener-users"],
                    },
                }

        authentik = _Auth()

    app_module.oauth = _DummyOAuth()
    app_module.oidc_client_id = "dooropener-client"
    app_module.oidc_issuer = "https://auth.example.com"

    c = client_app()
    with c.session_transaction() as s:
        s["oidc_state"] = "expected"
        s["oidc_nonce"] = "abc"
    r = c.get("/oidc/callback?state=expected", follow_redirects=False)
    assert r.status_code == 401


def test_oidc_callback_success_sets_session_and_redirects(monkeypatch):
    import app as app_module

    class _DummyOAuth:
        class _Auth:
            def authorize_access_token(self):
                return {
                    "id_token": "dummy",
                    "userinfo": {
                        "aud": "dooropener-client",
                        "iss": "https://auth.example.com",
                        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
                        "nonce": "xyz",
                        "email": "carol@example.com",
                        "groups": ["dooropener-users"],
                    },
                }

        authentik = _Auth()

    app_module.oauth = _DummyOAuth()
    app_module.oidc_client_id = "dooropener-client"
    app_module.oidc_issuer = "https://auth.example.com"

    c = client_app()
    with c.session_transaction() as s:
        s["oidc_state"] = "expected"
        s["oidc_nonce"] = "xyz"
    r = c.get("/oidc/callback?state=expected", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("Location", "").endswith("/")


def test_oidc_logout_no_logout_url_returns_500(monkeypatch):
    import app as app_module

    class _DummyOAuth:
        pass

    app_module.oauth = _DummyOAuth()
    app_module.oidc_issuer = "https://auth.example.com"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {}

    c = client_app()
    with patch("requests.get", return_value=mock_resp):
        r = c.get("/oidc/logout")
        assert r.status_code == 500


def test_battery_out_of_range_and_none_paths(monkeypatch):
    # Out of range value
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"state": "150"}
    with patch("requests.get", return_value=mock_response):
        c = client_app()
        response = c.get("/battery")
        assert response.get_json()["level"] is None

    # None value
    mock_response2 = MagicMock()
    mock_response2.status_code = 200
    mock_response2.json.return_value = {"state": None}
    with patch("requests.get", return_value=mock_response2):
        c = client_app()
        response2 = c.get("/battery")
        assert response2.get_json()["level"] is None


def test_admin_logs_old_format_parsing(monkeypatch):
    # Old style: "timestamp - ip - user - status - details"
    old_line = "2025-09-01T12:00:00Z - 1.2.3.4 - alice - SUCCESS - Door opened\n"
    # Monkeypatch open to return this line
    from io import StringIO

    file_obj = StringIO(old_line)
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", return_value=file_obj),
    ):
        c = client_app()
        with c.session_transaction() as s:
            s["admin_authenticated"] = True
            s["admin_login_time"] = datetime.now(timezone.utc).isoformat()
        r = c.get("/admin/logs")
        assert r.status_code == 200
        data = r.get_json()
        assert any(row.get("user") == "alice" for row in data.get("logs", []))
