import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from users_store import UsersStore


def client_app():
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def temp_users_file():
    """Create a temporary users.json file for testing."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_users_store(temp_users_file, monkeypatch):
    """Mock the global users_store with a temporary file."""
    import app as app_module

    store = UsersStore(temp_users_file)
    monkeypatch.setattr(app_module, "users_store", store)
    return store


def _admin_session(client):
    """Helper to create an authenticated admin session."""
    with client.session_transaction() as s:
        s["admin_authenticated"] = True
        s["admin_login_time"] = datetime.now(timezone.utc).isoformat()


def test_admin_users_list_empty(mock_users_store, monkeypatch):
    """Test listing users when no users exist."""
    import app as app_module

    # Clear any config users
    monkeypatch.setattr(app_module, "user_pins", {})

    c = client_app()
    _admin_session(c)

    response = c.get("/admin/users")
    assert response.status_code == 200

    data = response.get_json()
    assert "users" in data
    assert len(data["users"]) == 0


def test_admin_users_list_with_json_users(mock_users_store, monkeypatch):
    """Test listing users with JSON store users."""
    import app as app_module

    # Clear any config users
    monkeypatch.setattr(app_module, "user_pins", {})

    # Create some test users
    mock_users_store.create_user("alice", "1234")
    mock_users_store.create_user("bob", "5678")
    mock_users_store.touch_user("alice")  # Increment usage counter

    c = client_app()
    _admin_session(c)

    response = c.get("/admin/users")
    assert response.status_code == 200

    data = response.get_json()
    users = data["users"]
    assert len(users) == 2

    # Check user properties
    alice = next(u for u in users if u["username"] == "alice")
    bob = next(u for u in users if u["username"] == "bob")

    assert alice["source"] == "store"
    assert alice["can_edit"] is True
    assert alice["times_used"] == 1
    assert bob["times_used"] == 0


def test_admin_users_list_with_config_users(mock_users_store, monkeypatch):
    """Test listing users with config-only users."""
    import app as app_module

    # Mock config users
    config_pins = {"charlie": "9999", "dave": "0000"}
    monkeypatch.setattr(app_module, "user_pins", config_pins)

    c = client_app()
    _admin_session(c)

    response = c.get("/admin/users")
    assert response.status_code == 200

    data = response.get_json()
    users = data["users"]
    assert len(users) == 2

    # Check config users
    charlie = next(u for u in users if u["username"] == "charlie")
    dave = next(u for u in users if u["username"] == "dave")

    assert charlie["source"] == "config"
    assert charlie["can_edit"] is False
    assert "times_used" not in charlie  # Config users don't have usage tracking
    assert dave["source"] == "config"
    assert dave["can_edit"] is False


def test_admin_users_list_mixed_sources(mock_users_store, monkeypatch):
    """Test listing users with both JSON and config users."""
    import app as app_module

    # Create JSON user
    mock_users_store.create_user("alice", "1234")

    # Mock config users
    config_pins = {"bob": "5678", "charlie": "9999"}
    monkeypatch.setattr(app_module, "user_pins", config_pins)

    c = client_app()
    _admin_session(c)

    response = c.get("/admin/users")
    assert response.status_code == 200

    data = response.get_json()
    users = data["users"]
    assert len(users) == 3

    # JSON user should be first (store users come first)
    alice = next(u for u in users if u["username"] == "alice")
    bob = next(u for u in users if u["username"] == "bob")

    assert alice["source"] == "store"
    assert alice["can_edit"] is True
    assert bob["source"] == "config"
    assert bob["can_edit"] is False


def test_admin_users_create(mock_users_store):
    """Test creating a new user via API."""
    c = client_app()
    _admin_session(c)

    response = c.post(
        "/admin/users", json={"username": "newuser", "pin": "1234", "active": True}
    )
    assert response.status_code == 201

    data = response.get_json()
    assert data["status"] == "created"

    # Verify user was created
    users = mock_users_store.list_users()["users"]
    assert len(users) == 1
    user = users[0]
    assert user["username"] == "newuser"
    assert user["active"] is True
    assert user["times_used"] == 0


def test_admin_users_create_duplicate(mock_users_store):
    """Test creating a duplicate user fails."""
    mock_users_store.create_user("existing", "1234")

    c = client_app()
    _admin_session(c)

    response = c.post(
        "/admin/users", json={"username": "existing", "pin": "5678", "active": True}
    )
    assert response.status_code == 409

    data = response.get_json()
    assert "already exists" in data["error"]


def test_admin_users_create_invalid_data(mock_users_store):
    """Test creating user with invalid data."""
    c = client_app()
    _admin_session(c)

    # Missing username
    response = c.post("/admin/users", json={"pin": "1234", "active": True})
    assert response.status_code == 400

    # Invalid PIN (too short)
    response = c.post(
        "/admin/users", json={"username": "test", "pin": "12", "active": True}
    )
    assert response.status_code == 400


def test_admin_users_update(mock_users_store):
    """Test updating an existing user."""
    mock_users_store.create_user("testuser", "1234")

    c = client_app()
    _admin_session(c)

    response = c.put("/admin/users/testuser", json={"pin": "5678", "active": False})
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "updated"

    # Verify user was updated
    users = mock_users_store.list_users()["users"]
    user = users[0]
    assert user["active"] is False


def test_admin_users_update_nonexistent(mock_users_store):
    """Test updating a user that doesn't exist."""
    c = client_app()
    _admin_session(c)

    response = c.put("/admin/users/nonexistent", json={"pin": "1234", "active": True})
    assert response.status_code == 404

    data = response.get_json()
    assert "not found" in data["error"]


def test_admin_users_delete(mock_users_store):
    """Test deleting a user."""
    mock_users_store.create_user("testuser", "1234")

    c = client_app()
    _admin_session(c)

    response = c.delete("/admin/users/testuser")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "deleted"

    # Verify user was deleted
    users = mock_users_store.list_users()["users"]
    assert len(users) == 0


def test_admin_users_delete_nonexistent(mock_users_store):
    """Test deleting a user that doesn't exist."""
    c = client_app()
    _admin_session(c)

    response = c.delete("/admin/users/nonexistent")
    assert response.status_code == 404

    data = response.get_json()
    assert "not found" in data["error"]


def test_admin_users_migrate_single(mock_users_store, monkeypatch):
    """Test migrating a single user from config to JSON store."""
    import app as app_module

    # Mock config users and config file operations
    config_pins = {"configuser": "1234"}
    monkeypatch.setattr(app_module, "user_pins", config_pins)

    mock_config = MagicMock()
    mock_config.remove_option.return_value = None
    mock_config.write = MagicMock()

    with (
        patch("configparser.ConfigParser", return_value=mock_config),
        patch("builtins.open", MagicMock()),
    ):
        c = client_app()
        _admin_session(c)

        response = c.post("/admin/users/configuser/migrate")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "migrated"

        # Verify user was created in JSON store
        users = mock_users_store.list_users()["users"]
        assert len(users) == 1
        user = users[0]
        assert user["username"] == "configuser"
        assert user["times_used"] == 0


def test_admin_users_migrate_all(mock_users_store, monkeypatch):
    """Test migrating all config users to JSON store."""
    import app as app_module

    # Mock config users
    config_pins = {"user1": "1111", "user2": "2222", "user3": "3333"}
    monkeypatch.setattr(app_module, "user_pins", config_pins)

    mock_config = MagicMock()
    mock_config.remove_option.return_value = None
    mock_config.write = MagicMock()

    with (
        patch("configparser.ConfigParser", return_value=mock_config),
        patch("builtins.open", MagicMock()),
    ):
        c = client_app()
        _admin_session(c)

        response = c.post("/admin/users/migrate-all")
        assert response.status_code == 200

        data = response.get_json()
        assert data["migrated"] == 3
        assert data["failed"] == []

        # Verify all users were created in JSON store
        users = mock_users_store.list_users()["users"]
        assert len(users) == 3
        usernames = {u["username"] for u in users}
        assert usernames == {"user1", "user2", "user3"}


def test_admin_users_migrate_all_no_config_users(mock_users_store, monkeypatch):
    """Test migrate-all when no config users exist."""
    import app as app_module

    # No config users
    monkeypatch.setattr(app_module, "user_pins", {})

    c = client_app()
    _admin_session(c)

    response = c.post("/admin/users/migrate-all")
    assert response.status_code == 200

    data = response.get_json()
    assert data["migrated"] == 0
    assert data["failed"] == []


def test_admin_users_unauthenticated_access(mock_users_store):
    """Test that unauthenticated requests are rejected."""
    c = client_app()

    # Test all user management endpoints
    endpoints = [
        ("GET", "/admin/users"),
        ("POST", "/admin/users"),
        ("PUT", "/admin/users/test"),
        ("DELETE", "/admin/users/test"),
        ("POST", "/admin/users/test/migrate"),
        ("POST", "/admin/users/migrate-all"),
    ]

    for method, endpoint in endpoints:
        if method == "GET":
            response = c.get(endpoint)
        elif method == "POST":
            response = c.post(endpoint, json={})
        elif method == "PUT":
            response = c.put(endpoint, json={})
        elif method == "DELETE":
            response = c.delete(endpoint)

        assert response.status_code == 401
        data = response.get_json()
        assert "Authentication required" in data["error"]


def test_times_used_counter_integration(mock_users_store, monkeypatch):
    """Test that times_used counter integrates with door opening."""
    import app as app_module

    # Create a user and clear config users
    mock_users_store.create_user("testuser", "1234")
    monkeypatch.setattr(app_module, "user_pins", {})

    # Mock successful door opening
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None

    # Mock config values
    monkeypatch.setattr(app_module, "test_mode", False)
    monkeypatch.setattr(app_module, "entity_id", "switch.door")
    monkeypatch.setattr(app_module, "ha_url", "http://localhost:8123")
    monkeypatch.setattr(app_module, "ha_headers", {"Authorization": "Bearer token"})

    with patch("requests.post", return_value=mock_response):
        c = client_app()

        # Simulate door opening
        response = c.post(
            "/open-door",
            json={"pin": "1234"},
            headers={"User-Agent": "test-agent", "Accept-Language": "en-US"},
        )

        # Should succeed
        assert response.status_code == 200

        # Check that times_used was incremented
        users = mock_users_store.list_users()["users"]
        user = users[0]
        assert user["times_used"] == 1
        assert user["last_used_at"] is not None


def test_user_management_ui_data_structure(mock_users_store):
    """Test that the API returns data in the format expected by the UI."""
    # Create users with different states
    mock_users_store.create_user("active_user", "1111")
    mock_users_store.create_user("inactive_user", "2222")
    mock_users_store.update_user("inactive_user", active=False)
    mock_users_store.touch_user("active_user")
    mock_users_store.touch_user("active_user")  # Use twice

    c = client_app()
    _admin_session(c)

    response = c.get("/admin/users")
    assert response.status_code == 200

    data = response.get_json()
    users = data["users"]

    # Check required fields for UI
    for user in users:
        assert "username" in user
        assert "active" in user
        assert "source" in user
        assert "can_edit" in user
        assert "created_at" in user
        assert "last_used_at" in user

        # JSON store users should have times_used
        if user["source"] == "store":
            assert "times_used" in user
            assert isinstance(user["times_used"], int)

    # Check specific user data
    active_user = next(u for u in users if u["username"] == "active_user")
    inactive_user = next(u for u in users if u["username"] == "inactive_user")

    assert active_user["active"] is True
    assert active_user["times_used"] == 2
    assert inactive_user["active"] is False
    assert inactive_user["times_used"] == 0
