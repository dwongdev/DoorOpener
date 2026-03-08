def make_client():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_auth_status_defaults(client=None):
    client = client or make_client()
    resp = client.get("/auth/status")
    assert resp.status_code == 200
    data = resp.get_json()
    # OIDC disabled by default in example tests
    assert "oidc_enabled" in data
    assert data["oidc_authenticated"] in (False, True)


def test_auth_status_with_session():
    # Simulate OIDC being enabled by providing a truthy oauth object
    import app as app_module

    app_module.oauth = object()
    client = make_client()
    with client.session_transaction() as s:
        s["oidc_authenticated"] = True
        s["oidc_user"] = "alice@example.com"
        s["oidc_groups"] = ["dooropener-users"]
    resp = client.get("/auth/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["oidc_authenticated"] is True
    assert data["user"] == "alice@example.com"
    assert "dooropener-users" in data.get("groups", [])


def test_open_door_pinless_oidc_allowed(monkeypatch):
    import app as app_module

    # Ensure policy allows pinless open and test mode avoids HA calls
    app_module.require_pin_for_oidc = False
    app_module.oidc_user_group = "dooropener-users"
    app_module.test_mode = True

    client = make_client()
    with client.session_transaction() as s:
        s["oidc_authenticated"] = True
        s["oidc_user"] = "alice"
        s["oidc_groups"] = ["dooropener-users"]
        # Provide a valid future expiration for the OIDC session
        import time as _time

        s["oidc_exp"] = int(_time.time()) + 3600

    resp = client.post("/open-door", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "Welcome home" in data["message"]


def test_open_door_pinless_blocked_when_require_pin(monkeypatch):
    import app as app_module

    app_module.require_pin_for_oidc = True
    app_module.oidc_user_group = ""  # any user allowed, but PIN still required
    app_module.test_mode = True

    client = make_client()
    with client.session_transaction() as s:
        s["oidc_authenticated"] = True
        s["oidc_user"] = "bob"
        s["oidc_groups"] = ["dooropener-users"]
        import time as _time

        s["oidc_exp"] = int(_time.time()) + 3600

    resp = client.post("/open-door", json={})
    # No PIN provided -> should be a 400 requiring PIN
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "PIN" in data["message"]


def test_open_door_pinless_expired_oidc(monkeypatch):
    import app as app_module

    app_module.require_pin_for_oidc = False
    app_module.oidc_user_group = "dooropener-users"
    app_module.test_mode = True

    client = make_client()
    with client.session_transaction() as s:
        s["oidc_authenticated"] = True
        s["oidc_user"] = "dana"
        s["oidc_groups"] = ["dooropener-users"]
        # Expired exp in the past
        s["oidc_exp"] = 1

    resp = client.post("/open-door", json={})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["status"] == "error"
    assert "expired" in data["message"].lower()


def test_login_sets_state_and_nonce_and_calls_authorize_redirect(monkeypatch):
    import app as app_module

    # Dummy provider to intercept authorize_redirect
    class _DummyProvider:
        def authorize_redirect(self, redirect_uri=None, state=None, nonce=None):
            assert redirect_uri
            assert state and nonce  # state/nonce must be provided
            from flask import redirect

            return redirect("/_dummy_redirect")

    class _DummyOAuth:
        def __init__(self):
            self.authentik = _DummyProvider()

    app_module.oauth = _DummyOAuth()

    client = make_client()
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/_dummy_redirect" in resp.headers.get("Location", "")


def test_oidc_callback_invalid_state(monkeypatch):
    import app as app_module

    # Ensure oauth object exists so callback doesn't short-circuit
    class _DummyOAuth:
        pass

    app_module.oauth = _DummyOAuth()

    client = make_client()
    # Seed expected state in session
    with client.session_transaction() as s:
        s["oidc_state"] = "expected"
        s["oidc_nonce"] = "nonce"
    # Provide wrong state so we fail before token exchange
    resp = client.get("/oidc/callback?state=wrong", follow_redirects=False)
    assert resp.status_code == 401


def test_open_door_pinless_blocked_when_group_not_allowed(monkeypatch):
    import app as app_module

    app_module.require_pin_for_oidc = False
    app_module.oidc_user_group = "dooropener-users"  # require specific group
    app_module.test_mode = True

    client = make_client()
    with client.session_transaction() as s:
        s["oidc_authenticated"] = True
        s["oidc_user"] = "charlie"
        s["oidc_groups"] = ["some-other-group"]
        import time as _time

        s["oidc_exp"] = int(_time.time()) + 3600

    resp = client.post("/open-door", json={})
    # Not in allowed group -> PIN required path triggers 400 when missing
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "PIN" in data["message"]
