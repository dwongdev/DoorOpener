[![CI](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/ci.yml)
[![Docker Build](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/docker-build.yml/badge.svg?branch=main)](https://github.com/Sloth-on-meth/DoorOpener/actions/workflows/docker-build.yml)
![Version 1.12](https://img.shields.io/badge/version-1.12.1-blue?style=flat-square)
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q81T7CVO)

<details>
  <summary><strong>🚨 Help Wanted (expand)</strong></summary>

**Home Assistant Add-on:** I couldn't figure out how to package this as a proper HA add-on. If you know how, please open a PR. Any solution must keep standalone Docker usage working.

**Security review:** The OIDC implementation is functional but hasn't been independently audited. If you have experience with OIDC/OAuth2 security, feedback and PRs are very welcome.

</details>

---

# 🚪 DoorOpener

A web-based keypad for controlling smart door locks via Home Assistant. PIN-protected with per-user codes, SSO login, rate limiting, and a dark glassmorphism UI.

<img width="1920" height="923" alt="keypad" src="https://github.com/user-attachments/assets/51f2e836-578d-4782-9156-3ba6e6752b59" />
<img width="1197" height="462" alt="admin" src="https://github.com/user-attachments/assets/edb8a1ab-0767-43fa-9238-0ccd41e1b4fd" />
<img width="1198" height="759" alt="image" src="https://github.com/user-attachments/assets/d84d9835-3a79-4be8-aebc-51fbe7f157ae" />

## Features

- Visual 3×4 keypad with auto-submit on valid PIN length
- Per-user PINs (4–8 digits), stored in a JSON user store
- Admin dashboard — user management, audit logs, leaderboard, live stats
- OIDC/SSO login (Authentik) with optional pinless door open
- Audio feedback (success chimes, failure sounds) and haptic on mobile
- Real-time battery monitoring for Zigbee devices (polls every 60 s)
- Multi-layer rate limiting: per-IP, per-session, and global
- Brute-force lockout with visual countdown on the keypad
- Security headers (CSP, XSS protection, clickjacking prevention)
- PWA — installable, works offline via service worker
- Dark mode (auto, follows OS preference)
- Supports `switch`, `lock`, and `input_boolean` HA entities
- Test mode for safe development without triggering the actual door

---

## Quick Start

### Docker Compose (recommended)

```yaml
services:
  dooropener:
    image: ghcr.io/sloth-on-meth/dooropener:latest
    container_name: dooropener
    env_file: .env
    ports:
      - "${DOOROPENER_PORT:-6532}:${DOOROPENER_PORT:-6532}"
    volumes:
      - ./config.ini:/app/config.ini:ro
      - ./users.json:/app/users.json
      - ./logs:/app/logs
    restart: unless-stopped
```

```bash
git clone https://github.com/Sloth-on-meth/DoorOpener.git && cd DoorOpener
cp config.ini.example config.ini   # edit with your HA URL, token, entity
cp .env.example .env               # set FLASK_SECRET_KEY at minimum
docker compose up -d
```

Then open `http://your-server:6532`.

### Build locally

```bash
docker build -t dooropener:latest .
docker run -d --env-file .env \
  -v $(pwd)/config.ini:/app/config.ini:ro \
  -v $(pwd)/users.json:/app/users.json \
  -v $(pwd)/logs:/app/logs \
  -p 6532:6532 dooropener:latest
```

### Without Docker

```bash
pip install -r requirements.txt
python app.py
```

---

## Configuration

### .env

```bash
FLASK_SECRET_KEY=change-me-to-something-long-and-random   # required
DOOROPENER_PORT=6532          # default 6532
TZ=Europe/Amsterdam           # default UTC
PUID=1000                     # aligns container user to your host user
PGID=1000
UMASK=002
SESSION_COOKIE_SECURE=true    # set false only for local HTTP dev
```

> The image follows the linuxserver.io `PUID`/`PGID` convention. On startup, the entrypoint drops privileges to the specified user so logs are written with your host uid — no manual `chown` needed.

### config.ini

```ini
[HomeAssistant]
url = http://homeassistant.local:8123
token = your_long_lived_access_token
switch_entity = switch.your_door_opener
# ca_bundle = /etc/dooropener/ha-ca.pem   # custom CA for self-signed HA certs

[admin]
admin_password = change-me

[server]
port = 6532
test_mode = false
67mode = false   # enable 6-7 easter egg

[security]
max_attempts = 5               # failed attempts per IP before block
block_time_minutes = 5
max_global_attempts_per_hour = 50
session_max_attempts = 3       # failed attempts per session before block
```

### Self-signed Home Assistant certificate

Mount your CA bundle and point `ca_bundle` at it:

```yaml
volumes:
  - ./certs/ha-ca.pem:/etc/dooropener/ha-ca.pem:ro
```

```ini
[HomeAssistant]
ca_bundle = /etc/dooropener/ha-ca.pem
```

Alternatively, set `REQUESTS_CA_BUNDLE=/etc/dooropener/ha-ca.pem` as an environment variable.

---

## User Management

DoorOpener stores users in `users.json`. Manage them through the admin dashboard — no restarts needed.

**Admin UI features:**
- Create, edit, delete users
- Activate / deactivate without deletion
- View creation date, last used, and open count
- Clear logs (test data or all)



---

## OIDC / SSO (Authentik)

> This integration works but is a first-pass implementation. It has not been independently audited. Use at your own risk and please open issues/PRs with fixes.

```ini
[oidc]
enabled = false
issuer = https://auth.example.com/application/o/dooropener
client_id = your_client_id
client_secret = your_client_secret
redirect_uri = https://your.domain/oidc/callback

# Group required to access admin dashboard (optional)
admin_group = dooropener-admins

# Group allowed to open the door via OIDC (leave empty = all authenticated users)
user_group = dooropener-users

# If true, OIDC users must still enter a PIN (no pinless open)
require_pin_for_oidc = false
```

When OIDC is enabled, a **Login with SSO** button appears on the keypad. Authenticated users in `user_group` can open the door without a PIN (unless `require_pin_for_oidc = true`).

> If running behind a reverse proxy over HTTP for local dev, set `SESSION_COOKIE_SECURE=false` so the browser sends the session cookie.

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Keypad UI |
| `POST` | `/open-door` | Open the door (JSON body: `{"pin": "1234"}`) |
| `GET` | `/battery` | Battery level for configured Zigbee device |
| `GET` | `/auth-status` | Current OIDC auth state |
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `GET` | `/admin` | Admin dashboard UI |
| `POST` | `/admin/auth` | Admin login |
| `GET` | `/admin/logs` | Audit log entries (JSON) |
| `GET` | `/admin/users` | User list (JSON) |
| `POST` | `/admin/users` | Create user |
| `PUT` | `/admin/users/<name>` | Update user |
| `DELETE` | `/admin/users/<name>` | Delete user |

---

## Easter Egg

Type `6767` on the keypad to trigger a full-screen 6-7 animation with confetti, an 8-bit fanfare, and haptic feedback.

Enable in `config.ini`:

```ini
[server]
67mode = true
```

Disabled by default — no client-side code is shipped when off.

---

## License

MIT — see [LICENSE](LICENSE).
