[![CI](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/ci.yml)
[![Docker Build](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/docker-build.yml/badge.svg?branch=main)](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/docker-build.yml)
![Version 1.10.0](https://img.shields.io/badge/version-1.10.0-blue?style=flat-square)
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q81T7CVO)
<details>
  <summary><strong>🚨 Help Wanted: Security / HA Addon (please expand)</strong></summary>

  
  
  ### Home Assistant Add-on Needed!
  **I couldn't figure out how to turn this project into a proper Home Assistant add-on. If you know how, please open a PR!**

  > **Important:** Any add-on solution must not break standalone usage. The project must remain fully usable both as a Home Assistant add-on _and_ as a standalone app (Docker).

  ### Security audit needed!
  > I’ve implemented an OIDC setup with some security measures in place, but I’m not fully confident in how robust the implementation is. I’d really appreciate someone with experience taking a look and providing feedback on potential improvements.

</details>

---

# 🚪 DoorOpener

A pretty web interface for controlling smart door openers via Home Assistant. Features a modern glass-morphism UI with visual keypad, per-user PINs, audio feedback, battery monitoring, and comprehensive security.





<img width="2554" height="1187" alt="image" src="https://github.com/user-attachments/assets/e9e2fd6c-aa32-4ea1-933f-668fad3fbfc4" />

<img width="2554" height="1187" alt="image" src="https://github.com/user-attachments/assets/4d5259fa-ee7b-4d03-a02b-b77301cebf0c" />

## What It Does

DoorOpener provides a web-based keypad interface to remotely open doors connected to Home Assistant. Users enter their personal PIN on a visual keypad or login with SSO, and the system securely communicates with Home Assistant to trigger the door opener.

**Key Features:**
- Visual 3x4 keypad interface with auto-submit
- Individual PINs for each user with JSON-based user management
- Audio feedback (success chimes, failure sounds)
- Real-time battery monitoring for Zigbee devices
- Multi-layer security with rate limiting and IP blocking
- **NEW**: Complete admin UI with user management and migration tools
- **NEW**: Toast notifications and modern responsive design
- Test mode for safe development
- **Supports Home Assistant `switch`, `lock`, and `input_boolean` entities**

## Quick Start

### Docker (Recommended)

Use Docker Compose (recommended). It handles environment, volumes, and permissions cleanly.

```yaml
services:
  dooropener:
    image: ghcr.io/sloth-on-meth/dooropener:latest
    container_name: dooropener
    environment:
      - DOOROPENER_PORT=${DOOROPENER_PORT:-6532}
      - TZ=${TZ:-UTC}
      - PUID=${PUID:-1000}
      - PGID=${PGID:-1000}
      - UMASK=${UMASK:-002}
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
      - SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-true}
    ports:
      - "${DOOROPENER_PORT:-6532}:${DOOROPENER_PORT:-6532}"
    volumes:
      - ./config.ini:/app/config.ini:ro
      - ./logs:/app/logs
    restart: unless-stopped
```

Steps:
1. `git clone https://github.com/Sloth-on-meth/DoorOpener.git && cd DoorOpener`
2. `cp config.ini.example config.ini` and edit it.
3. `cp .env.example .env` and adjust values (TZ, PUID/PGID, etc.).
4. `docker compose up -d`

#### Building Locally (Optional)
If you want to build the image yourself:
```bash
docker build -t dooropener:latest .
docker run -d --env-file .env -v $(pwd)/config.ini:/app/config.ini:ro -v $(pwd)/logs:/app/logs -p 6532:6532 dooropener:latest
```

 


<!--
#### Using the public ghcr.io image

(Registry-based deployment is currently disabled)
-->


## Configuration

### Environment Variables (.env file)

```bash
# Port configuration (optional, defaults to 6532)
DOOROPENER_PORT=6532

# Timezone (optional, defaults to UTC)
TZ=Europe/Amsterdam

# Map the runtime user/group inside the container to your host user
# Helps the app write to ./logs without manual chown
PUID=1000
PGID=1000

# Default permissions for created files/dirs
UMASK=002

# Security/session settings (strongly recommended in production)
FLASK_SECRET_KEY=please-change-me
# When running behind HTTPS (reverse proxy), leave as true
# For local HTTP testing only, set to false so cookies are sent
SESSION_COOKIE_SECURE=true
```

### PUID/PGID and permissions (linuxserver-style)

This image supports `PUID`, `PGID` and `UMASK` to avoid host-side chown. On startup, the entrypoint aligns the runtime user/group to those IDs and ensures `/app/logs` is writable, then drops privileges. Keep `config.ini` mounted read-only and bind `./logs` to persist logs.

### Logs

- Application access logs: `/app/logs/log.txt` (bind mount `./logs:/app/logs`)
- Gunicorn/access output: container stdout/stderr (visible via `docker logs`)

### Application Config (config.ini)

```ini
[HomeAssistant]
url = http://homeassistant.local:8123
token = your_long_lived_access_token
switch_entity = switch.your_door_opener

# Optional: trust a custom CA bundle (PEM) for HTTPS to Home Assistant
# Example: /etc/dooropener/ha-ca.pem
# If provided and readable, the app verifies TLS using this bundle.
# If empty/not set, the system trust store is used (default).
ca_bundle =

[pins]
# TO BE DEPRECATED: Legacy PIN storage - will be removed in a future version
# Migrate to JSON store via Admin UI for full management capabilities
# alice = 1234
# bob = 5678

[admin]
admin_password = secure_password

[server]
# Overridden by DOOROPENER_PORT env var if set
port = 6532
# Set to true for testing without opening door
test_mode = false

[security]
# Maximum failed attempts per IP before blocking
max_attempts = 5 
# Block time in minutes after max attempts reached
block_time_minutes = 5
# Maximum global attempts per hour across all users
max_global_attempts_per_hour = 50
# Maximum failed attempts per session before blocking
session_max_attempts = 3
```

### OIDC (Authentik) — Experimental

> IMPORTANT: This OIDC/Authentik integration is a rudimentary, first-pass implementation. It has not been fully verified end‑to‑end in production. It may not work in your setup. Use at your own risk and please open issues/PRs with fixes.

DoorOpener can optionally integrate with Authentik using in‑app OIDC. When enabled, users can sign in via SSO, and—optionally—open the door without a PIN.

```ini
[oidc]
enabled = false                     # Set to true to enable OIDC
issuer = https://auth.example.com/application/o/dooropener
client_id = your_client_id
client_secret = your_client_secret
redirect_uri = https://your.domain/oidc/callback

# Optional group required for admin dashboard access
admin_group = dooropener-admins

# Optional group allowed to open the door via OIDC (pinless)
# Leave empty to allow any authenticated OIDC user
user_group = dooropener-users

# If true, OIDC users still must enter a PIN (no pinless open)
require_pin_for_oidc = false
```

## User Management & Migration

### JSON User Store

DoorOpener v1.10.0+ includes a modern JSON-based user management system alongside the traditional config.ini [pins] section. The JSON store (`users.json`) provides:

- **Full CRUD operations**: Create, edit, delete users via admin UI
- **User activation/deactivation**: Temporarily disable users without deletion
- **Persistent storage**: Data survives container restarts via volume binding
- **Priority system**: JSON store users override config.ini entries

### Migrating from config.ini to JSON Store

**Why migrate?**
- **Future-proof**: config.ini [pins] will be deprecated and removed in a future version
- Gain full user management capabilities (edit PINs, activate/deactivate)
- Modern admin UI with toast notifications and responsive design
- No need to restart containers when managing users
- Persistent user data with automatic backups

**Migration Process:**

1. **Access Admin UI**: Navigate to `http://your-server:6532/admin` and login
2. **Switch to Users Tab**: Click the "👥 Users" tab in the admin dashboard
3. **Review Config Users**: You'll see existing config.ini users marked as "Config-only"
4. **Bulk Migration**: Click the "⬇️ Migrate All" button
5. **Confirm**: Review the migration dialog and click "OK"
6. **Automatic Process**: 
   - Users are created in JSON store with existing PINs
   - Original entries are removed from config.ini
   - No service interruption or restarts required

**After Migration:**
- Users appear in the admin UI with full management options
- Edit PINs, activate/deactivate, or delete users as needed
- Add new users directly through the "➕ Add User" button
- All changes are immediate and persistent

**Volume Binding (Important):**
Ensure your docker-compose.yml includes the users.json volume bind:

```yaml
volumes:
  - ./config.ini:/app/config.ini:rw
  - ./logs:/app/logs
  - ./users.json:/app/users.json  # Required for persistence
```

### User Management Features

**Admin UI Capabilities:**
- **Create Users**: Add new users with custom PINs (4-8 digits)
- **Edit Users**: Modify existing user PINs
- **Activate/Deactivate**: Temporarily disable users without deletion
- **Delete Users**: Permanently remove users from the system
- **View Activity**: See creation dates, last used timestamps
- **Log Management**: Clear test data or all logs with confirmation

**Security Features:**
- All user management requires admin authentication
- Changes are logged with timestamps and admin details
- Atomic operations prevent data corruption
- Input validation for usernames and PINs

**Best Practices:**
- Migrate config.ini users early to gain full management capabilities
- Use descriptive usernames (alphanumeric, underscore, dash, dot allowed)
- Regularly review user activity via the admin dashboard
- Use "Clear Test Data" to remove development/testing log entries

Notes:
- In development over HTTP, set `SESSION_COOKIE_SECURE=false` (env) so the browser sends the session cookie.
- Set a stable secret across instances via `FLASK_SECRET_KEY` (env) or `[server] secret_key` in `config.ini`.
- The implementation is minimal and may require adjustments to claims (e.g., `groups`) depending on your Authentik setup.

**Configuration Priority:**
1. Environment variables (`.env` file) - highest priority
2. `config.ini` settings
3. Default values

### Self-signed certificates (Home Assistant)

If your Home Assistant uses a self-signed certificate, the recommended approach is to provide a custom CA bundle (PEM) and have DoorOpener verify TLS against it.

Options:

1. Config-based (recommended)

   - Add `ca_bundle = /etc/dooropener/ha-ca.pem` under `[HomeAssistant]` in `config.ini`.
   - Mount the file into the container as read-only.

   Docker Compose example:

   ```yaml
   services:
     dooropener:
       volumes:
         - ./config.ini:/app/config.ini:ro
         - ./certs/ha-ca.pem:/etc/dooropener/ha-ca.pem:ro
   ```

2. Environment variable (no code/config change)

   - Set one of these env vars so Python Requests uses your bundle:
     - `REQUESTS_CA_BUNDLE=/etc/dooropener/ha-ca.pem`
     - `SSL_CERT_FILE=/etc/dooropener/ha-ca.pem`

   Docker Compose example:

   ```yaml
   services:
     dooropener:
       environment:
         - REQUESTS_CA_BUNDLE=/etc/dooropener/ha-ca.pem
       volumes:
         - ./certs/ha-ca.pem:/etc/dooropener/ha-ca.pem:ro
   ```

Notes:

- Ensure the hostname in `url` (e.g., `https://homeassistant.local`) matches a Subject Alternative Name in the certificate.
- Build your PEM by concatenating the required certificates (root CA and any intermediates).

## Usage

1. **Access Interface** - Visit `http://localhost:6532`
2. **Enter PIN** - Use the visual keypad to enter your 4-8 digit PIN
3. **Auto-Submit** - Door opens automatically when valid PIN length is entered
4. **Admin Access** - Click gear icon for admin dashboard (view logs, manage users)

## Security Features

- **Configurable Rate Limiting** - Customizable failed attempt limits and block times
- **Multi-Layer Protection** - IP-based, session-based, and global rate limiting
- **Progressive Delays** - Increasing delays (1s→16s) after failed attempts
- **Session Tracking** - Prevents easy bypass of security measures  
- **Audit Logging** - All attempts logged with timestamps, IPs, and results
- **Input Validation** - PIN format validation and request sanitization
- **Security Headers** - XSS protection, clickjacking prevention, CSP

### Security Configuration

All security parameters are configurable via `config.ini`:

- `max_attempts` - Failed attempts per IP before blocking (default: 5)
- `block_time_minutes` - Block duration in minutes (default: 5)
- `max_global_attempts_per_hour` - Global rate limit across all users (default: 50)
- `session_max_attempts` - Failed attempts per session before blocking (default: 3)

## API Endpoints

- `GET /` - Main interface
- `POST /open-door` - Door control (requires PIN unless OIDC pinless is enabled and user is authorized)
- `GET /battery` - Battery level data
- `GET /admin` - Admin dashboard

## Development

**Test Mode:** Set `test_mode = true` in config to test interface without opening door.

**Manual Installation:**
```bash
pip install -r requirements.txt
python app.py
```

## License

Open source - see repository for details.
