"""Tests for previously uncovered routes and edge cases."""

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest


def client_app():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _admin_session(client):
    with client.session_transaction() as s:
        s["admin_authenticated"] = True
        s["admin_login_time"] = datetime.now(timezone.utc).isoformat()


def _std_headers():
    return {
        "User-Agent": "pytest-client/1.0 (+https://example.test)",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# /admin/check-auth
# ---------------------------------------------------------------------------


def test_check_auth_unauthenticated():
    c = client_app()
    r = c.get("/admin/check-auth")
    assert r.status_code == 200
    assert r.get_json()["authenticated"] is False


def test_check_auth_authenticated():
    c = client_app()
    _admin_session(c)
    r = c.get("/admin/check-auth")
    assert r.status_code == 200
    data = r.get_json()
    assert data["authenticated"] is True
    assert "login_time" in data


# ---------------------------------------------------------------------------
# /admin/logs/clear
# ---------------------------------------------------------------------------


def test_logs_clear_unauthenticated():
    c = client_app()
    r = c.post("/admin/logs/clear", json={"mode": "all"})
    assert r.status_code == 401


def test_logs_clear_invalid_mode():
    c = client_app()
    _admin_session(c)
    r = c.post("/admin/logs/clear", json={"mode": "invalid"})
    assert r.status_code == 400


def test_logs_clear_all(tmp_path):
    log_file = tmp_path / "attempts.log"
    log_file.write_text('{"timestamp":"2025-01-01","status":"FAIL"}\n')

    import app as app_module

    original = app_module.log_path
    app_module.log_path = str(log_file)
    try:
        c = client_app()
        _admin_session(c)
        r = c.post("/admin/logs/clear", json={"mode": "all"})
        assert r.status_code == 200
        assert r.get_json()["mode"] == "all"
        assert log_file.read_text() == ""
    finally:
        app_module.log_path = original


def test_logs_clear_test_only(tmp_path):
    log_file = tmp_path / "attempts.log"
    keep_line = (
        json.dumps({"timestamp": "2025-01-01", "status": "SUCCESS", "details": "real"})
        + "\n"
    )
    remove_line = (
        json.dumps(
            {
                "timestamp": "2025-01-01",
                "status": "FAIL",
                "details": "TEST MODE attempt",
            }
        )
        + "\n"
    )
    log_file.write_text(keep_line + remove_line)

    import app as app_module

    original = app_module.log_path
    app_module.log_path = str(log_file)
    try:
        c = client_app()
        _admin_session(c)
        r = c.post("/admin/logs/clear", json={"mode": "test_only"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["removed"] == 1
        assert data["kept"] == 1
        remaining = log_file.read_text()
        assert "real" in remaining
        assert "TEST MODE" not in remaining
    finally:
        app_module.log_path = original


def test_logs_clear_all_missing_file():
    """Clearing a log that doesn't exist should succeed gracefully."""
    import app as app_module

    original = app_module.log_path
    app_module.log_path = "/nonexistent/path/attempts.log"
    try:
        c = client_app()
        _admin_session(c)
        r = c.post("/admin/logs/clear", json={"mode": "all"})
        assert r.status_code == 200
    finally:
        app_module.log_path = original


# ---------------------------------------------------------------------------
# validate_pin_input / open-door PIN length boundaries
# ---------------------------------------------------------------------------


def test_open_door_pin_too_short(client):
    """3-digit PIN should be rejected with 400."""
    r = client.post("/open-door", json={"pin": "123"}, headers=_std_headers())
    assert r.status_code == 400


def test_open_door_pin_too_long(client):
    """9-digit PIN should be rejected with 400."""
    r = client.post("/open-door", json={"pin": "123456789"}, headers=_std_headers())
    assert r.status_code == 400


def test_open_door_pin_empty_string(client):
    """Empty string PIN should be rejected with 400."""
    r = client.post("/open-door", json={"pin": ""}, headers=_std_headers())
    assert r.status_code == 400


def test_open_door_non_json_body(client):
    """Non-JSON body should be rejected with 400."""
    r = client.post(
        "/open-door",
        data="pin=1234",
        headers={
            "User-Agent": "pytest-client/1.0 (+https://example.test)",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# UsersStore.effective_pins with inactive users
# ---------------------------------------------------------------------------


def test_effective_pins_inactive_user_excluded():
    """A user marked active=false in JSON store must not appear in effective pins."""
    from users_store import UsersStore

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        store = UsersStore(path)
        store.create_user("alice", "1234", active=True)
        store.create_user("bob", "5678", active=False)

        base = {"alice": "1234", "bob": "5678", "charlie": "9999"}
        effective = store.effective_pins(base)

        assert "alice" in effective
        assert "bob" not in effective  # deactivated in JSON
        assert "charlie" in effective  # only in base, implicitly active
    finally:
        os.unlink(path)


def test_effective_pins_invalid_pin_in_store_skipped():
    """A JSON user with an invalid pin (wrong length/non-digit) is not added."""
    from users_store import UsersStore

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        store = UsersStore(path)
        # Manually inject a bad pin directly into the store data
        store._load_file()
        store.data["users"]["badpin"] = {"pin": "ab", "active": True}
        store._save_atomic()

        effective = store.effective_pins({})
        assert "badpin" not in effective
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Fixture reusing conftest client for PIN boundary tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        with flask_app.app_context():
            yield c
