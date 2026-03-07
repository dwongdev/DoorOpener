from datetime import timedelta


def test_service_worker_endpoint(client):
    r = client.get("/service-worker.js")
    assert r.status_code in (200, 404)  # optional in some setups
    if r.status_code == 200:
        # Flask sets mimetype explicitly to application/javascript
        assert "javascript" in (r.mimetype or "")


def test_manifest_endpoint(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code in (200, 404)  # optional in some setups
    if r.status_code == 200:
        assert "application/manifest+json" in (r.mimetype or "")


def test_csp_directives_on_index(client):
    r = client.get("/")
    assert r.status_code == 200
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "connect-src 'self'" in csp


def test_counters_reset_on_success_after_no_block(client, monkeypatch):
    import app as app_module

    # Fix identifiers so we can inspect counters
    monkeypatch.setattr(
        app_module, "get_client_identifier", lambda: ("2.2.2.2", "sessReset", "idReset")
    )
    app_module.user_pins["ok"] = "9999"
    app_module.test_mode = True

    headers = {
        "User-Agent": "pytest-client/1.0 (+https://example.test)",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }

    # One failing attempt (wrong pin) should bump counters
    r1 = client.post("/open-door", json={"pin": "0000"}, headers=headers)
    assert r1.status_code in (401, 429)

    # Now a success attempt should reset counters and clear blocks
    r2 = client.post("/open-door", json={"pin": "9999"}, headers=headers)
    assert r2.status_code in (200, 502, 500)  # HA may be unreachable in CI

    assert app_module.ip_failed_attempts["idReset"] == 0
    assert app_module.session_failed_attempts["sessReset"] == 0
    assert (
        "idReset" not in app_module.ip_blocked_until
        or not app_module.ip_blocked_until["idReset"]
    )
    assert (
        "sessReset" not in app_module.session_blocked_until
        or not app_module.session_blocked_until["sessReset"]
    )


def test_counters_not_reset_on_success_when_block_active(client, monkeypatch):
    import app as app_module

    # Fix identifiers
    monkeypatch.setattr(
        app_module, "get_client_identifier", lambda: ("3.3.3.3", "sessBlock", "idBlock")
    )
    app_module.user_pins["ok2"] = "1111"
    app_module.test_mode = True

    # Apply active in-memory session block
    app_module.session_blocked_until[
        "sessBlock"
    ] = app_module.get_current_time() + timedelta(seconds=30)

    headers = {
        "User-Agent": "pytest-client/1.0 (+https://example.test)",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }

    r = client.post("/open-door", json={"pin": "1111"}, headers=headers)
    assert r.status_code == 429

    # Counters must not be reset during active block
    assert app_module.ip_failed_attempts.get("idBlock", 0) == 0
    assert app_module.session_failed_attempts.get("sessBlock", 0) == 0
    # Block must still be present
    assert app_module.session_blocked_until["sessBlock"] > app_module.get_current_time()
