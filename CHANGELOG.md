## v[1.11.0] - 2026-03-08

### 🎨 UI/UX
- **Dark mode** — full automatic dark theme via `prefers-color-scheme: dark`, covering keypad, battery widget, admin gear, PIN display, and all interactive states
- **Battery widget overhaul** — fill bar now correctly clips to the reported percentage using `overflow: hidden` + child `width: %`; null and out-of-range values render as 0% with a grey fill instead of broken display; widget auto-polls every 60 seconds without page reload
- **Keypad disabled state** — buttons grey out (`opacity: 0.35`, `pointer-events: none`) and become non-interactive for the full duration of a brute-force block countdown
- **GPU-accelerated popup animation** — access-granted/denied popups now animate with `transform: translateY()` instead of `top`, eliminating layout reflow on every frame
- **PIN placeholder** — "Enter PIN" placeholder no longer inherits `letter-spacing: 8px`; spacing is applied only to entered dot characters

### 🛠️ Technical
- **Atomic user store writes** — `users.json` is written via `tempfile.mkstemp` + `os.replace`, preventing file corruption if the process crashes mid-write
- **CSS consolidation** — merged two duplicate `.container` blocks and two duplicate `@media (max-width: 480px)` blocks; all inline styles moved to named CSS classes
- **Popup deduplication** — `showAccessDeniedPopup` and `showAccessGrantedPopup` unified into a single `showAccessPopup(id)` helper

### 🧪 Tests
- 13 new tests covering previously uncovered paths:
  - `/admin/check-auth` (authenticated and unauthenticated)
  - `/admin/logs/clear` (all modes, missing file, invalid mode, unauthenticated)
  - PIN length boundaries (too short, too long, empty, non-JSON body)
  - `UsersStore.effective_pins` with inactive users and invalid PINs in the store

### ⚙️ CI
- Python matrix expanded to **3.10 + 3.12**
- Pip caching added to all jobs
- `bandit` now fails the build on medium+ severity findings (removed `|| true`)
- `ruff` lint job no longer uses `continue-on-error`; `ruff format --check` step added
- Docker login switched from `GHCR_PAT` secret to `GITHUB_TOKEN` (no secret management needed)
- All actions pinned to `@v4` / `setup-python@v5`
- Redundant `pycodestyle` workflow removed (superseded by ruff)

---

## v[1.10.1] - 2025-12-09

### 🎨 UI/UX
- Added a fully responsive mobile view for the Users admin tab.
  - Users are rendered as touch-friendly cards on small screens with status badges and action buttons.
  - The desktop table remains unchanged; mobile now switches to cards for readability.

### 🐞 Fixes
- Corrected CSS so only the logs table is hidden on phones (users table/cards remain visible).
- Minor README cleanup (removed outdated notice).

---

## v[1.10.0] - 2025-09-16


> **⚠️ BREAKING CHANGE**: Starting with v1.10.0, user management has been completely redesigned with a new JSON-based user store. **Existing users in `config.ini` [pins] section need to be migrated!**

## 🔄 **Migration Required**

**If you have users configured in `config.ini` [pins] section:**

1. **Update to v1.10.0** (your existing users will continue to work temporarily)
2. **Access Admin Panel** → Navigate to `http://your-dooropener:5000/admin`
3. **Go to Users Tab** → Click on the "Users" tab in the admin interface
4. **Click "Migrate All"** → This will move all your config.ini users to the new JSON store
5. **Verify Migration** → Check that all users appear in the Users tab with "store" source

**Benefits of Migration:**
- ✅ Edit user PINs without restarting the container
- ✅ Activate/deactivate users instantly
- ✅ Track usage statistics ("Times Used" counter)
- ✅ Full user management via web interface
- ✅ No more manual config.ini editing

**⚠️ Important:** The `config.ini` [pins] section will be **deprecated** in a future version. Migrate now to avoid disruption!

---

## 🔧 **Migration Guide for v1.10.0**

**If you're upgrading from a previous version, follow these steps:**

### 1. **Update Docker Compose**

Add the new `users.json` volume bind and make `config.ini` read-write:

```yaml
services:
  dooropener:
    image: ghcr.io/sloth-on-meth/dooropener:latest
    volumes:
      - ./config.ini:/app/config.ini:rw  # ⚠️ Changed from :ro to :rw
      - ./users.json:/app/users.json    # 🆕 New volume for user data
      - ./logs:/app/logs
    # ... rest of your config
```

### 2. **Start Container & Migrate Users**

**Note:** The app will automatically create `users.json` when needed - no manual file creation required!

```bash
# Start the updated container
docker-compose up -d

# Access admin panel 
# Go to Users tab → Click "Migrate All" button
```

### 3. **Verify Migration**

- Check that all users appear in the Users tab with "store" source
- Test that PINs still work
- Your `config.ini` [pins] section will be automatically cleaned up

**Why these changes?**
- `config.ini:rw` - Allows automatic removal of migrated users from config
- `users.json` - New persistent storage for user data with advanced features

---

### 👥 User Management & Migration System
- **NEW**: Complete admin UI for user management with tabbed interface (Logs/Users)
- **NEW**: JSON-based user store (`users.json`) with atomic operations and host persistence
- **NEW**: "Migrate All" functionality to bulk migrate config-only users from `config.ini` to JSON store
- **NEW**: Full CRUD operations for JSON store users (Create, Edit, Delete, Activate/Deactivate)
- **NEW**: Toast notifications throughout admin UI replacing blocking alert dialogs
- **NEW**: Log management with "Clear All Logs" functionality
- **NEW**: Button busy states with inline progress indicators for long-running operations
- **NEW**: Usage tracking - "Times Used" counter for each user showing door access frequency
- **IMPROVED**: User PIN resolution now prioritizes JSON store over config.ini entries
- **IMPROVED**: Migration process removes users from config.ini after successful JSON store creation
- **IMPROVED**: Admin UI uses modern modals and responsive design patterns
- **IMPROVED**: "Migrate All" button intelligently shows/hides based on available config-only users
- **BREAKING**: Individual user migration removed - use "Migrate All" for bulk operations
- **DEPRECATION**: config.ini [pins] section will be removed in a future version - migrate to JSON store

### 🔧 Technical Improvements
- Added `users.json` volume bind in docker-compose.yml for data persistence
- Simplified config.ini writing to avoid temporary file permission issues
- Enhanced error handling and logging for user management operations
- Added `user_exists()` method to UsersStore class
- Improved admin session authentication across all user management endpoints
- Added `times_used` counter that increments on successful door access
- Enhanced `touch_user()` method with usage tracking and backward compatibility

### 📝 Migration Instructions
- Existing config.ini [pins] users can be migrated via Admin → Users → "Migrate All"
- Migration preserves existing PINs and removes entries from config.ini
- JSON store users gain full management capabilities (edit PIN, activate/deactivate)
- Usage statistics are automatically tracked for all JSON store users
- No downtime required - config and JSON users work simultaneously during transition

## v[1.9.0] - 2025-09-16

### 🔐 TLS & Self‑Signed Certificates
- Added support for trusting a custom CA bundle for Home Assistant HTTPS requests.
- New `[HomeAssistant] ca_bundle` option in `config.ini` allows pointing to a PEM bundle.
- When set and readable, all HA `requests.get/post` calls use `verify=<ca_bundle>`.
- When not set, default system trust store is used (`verify=True`).
- README updated with Docker compose mount examples and env var alternatives (`REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`).

### 🛡️ Security Headers
- Introduced per‑request CSP nonce and applied it to inline scripts in `templates/index.html` and `templates/admin.html`.
- CSP tightened to rely on nonces for scripts, with a safe fallback when nonce generation fails.

### 🔑 OIDC Logout Behavior
- Restored 500 responses when the OIDC well‑known or `end_session_endpoint` is missing to align with tests/expectations.

### 🧪 Tests
- Added SSL tests to ensure `verify=True` by default (no ca_bundle) and `verify=<path>` when a bundle is configured for both GET and POST HA calls.
- Adjusted admin auth tests to accept non‑blocking delay responses (HTTP 429) for progressive delays before blocking.

### 📝 CI & Linting
- pycodestyle step is now non‑blocking in CI (`continue-on-error: true`), emitting warnings instead of failing the job.
- Fixed PEP 8 style (E203/E302) and Ruff issues (`Response` typing, removed unused import).

### 📦 Version
- Bumped version to 1.9.0.

## v[1.8.0] - 2025-09-11

### 🚀 PWA & Installability
- Added Web App Manifest and Service Worker to enable install on mobile/desktop.
- Register Service Worker on load; added in-app "Install App" button (Android/Chrome).
- Manifest and icons wired; Apple touch icon supported via existing favicon.

### 🎛️ Keypad & UX
- Auto-submit is now debounced: users can type 4–8 digits; submit fires after a short pause.
- Keyboard auto-repeat is ignored to prevent floods from held keys.
- Submission lock prevents concurrent requests.
- "ACCESS GRANTED / DENIED" popups now appear above the glass card.

### 🔒 Security & Blocking
- Enforce active blocks even when a correct PIN or valid OIDC session is used.
- Persist session block across workers via signed cookie (`blocked_until_ts`).
- All block responses now include `blocked_until` (epoch seconds) for client countdowns.
- Frontend shows a live countdown toast until the block expires.

### 🧪 Tests
- Added tests verifying:
  - Correct PIN during active block still returns 429 and includes `blocked_until`.
  - Persisted session block denies OIDC pinless open and includes `blocked_until`.

### 🛠️ CI & Linting
- Removed Black from CI to avoid repo-vs-image formatting differences.
- `lint` job now runs Ruff only; separate pycodestyle workflow runs style checks without formatting.

### 📦 Version
- Bumped version to 1.8.0.

---

## v[1.7.0] - 2025-09-08

### 🔒 Security Enhancements (OIDC & App)
- OIDC now fully gated: all OIDC functionality is disabled unless the OAuth client is initialized and `enabled=true` in `[oidc]`.
- Added CSRF protection via `state` and replay protection via `nonce` in the OIDC flow.
- Enabled PKCE (`S256`).
- Strict token validation: issuer (`iss`) check, audience (`aud`) supports list or string, expiration (`exp`) and not‑before (`nbf`) with 60s leeway.
- Session fixation protection: session is cleared after successful token validation before setting auth data.
- Pinless open only when: OIDC enabled, session valid (non‑expired), user in allowed group (if configured), and `require_pin_for_oidc=false`.
- Hardened security headers: strong CSP, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'none'`, `Permissions-Policy`, strict referrer policy, and no‑cache on dynamic endpoints.
- Admin login protected with progressive delays and temporary session blocking; all attempts are now audit‑logged.

### 🧪 Tests & CI
- Expanded OIDC tests: state/nonce, expired session behavior, pinless success, invalid state rejection, login redirect behavior, and OIDC gating.
- CI pushes Docker image to GHCR on every push using `docker/login-action` with PAT or `GITHUB_TOKEN` fallback.

### 🐳 Docker & Runtime
- Adopted linuxserver.io‑style `PUID`/`PGID`/`UMASK` pattern for painless host permissions.
- New `entrypoint.sh` aligns runtime user/group to host IDs, ensures `/app/logs` is writable, applies umask, then drops privileges via `gosu`.
- Fixed Debian package availability in `python:3.9-slim` (trixie) by installing `passwd` (provides `useradd`/`groupadd`) instead of `shadow`.
- `docker-compose.yml` updated to include `PUID`, `PGID`, `UMASK` envs; `config.ini` stays read‑only; `logs/` is writeable.

### 📝 Logging & Observability
- Switched to `RotatingFileHandler` for both access and audit logs to prevent unbounded growth.
- All logs centralized under `/app/logs/` (mount `./logs:/app/logs`).

### 🎨 UI/UX
- Frontend SSO button visibility now strictly follows backend `oidc_enabled` flag.
- Added missing `openDoorWithSSO()` function to make SSO button functional.

### 📚 Documentation
- README refreshed with compose example, `PUID/PGID/UMASK`, `SESSION_COOKIE_SECURE`, and logging paths in linuxserver.io style.
- `.env.example` updated with new envs.
- `config.ini.example` gains optional `[oidc] public_key` for local token signature validation.

### 🙏 Acknowledgements
- Thanks to @hanneshier for the idea and contributions around the OIDC flow.
- Thanks to @remijn for fixing my docker build flow

---

## v[1.6.0] - 2025-09-04

### 🚀 Features & Improvements
- **Configurable Security Parameters**: All rate limiting and blocking thresholds are now settable in `[security]` section of `config.ini`.
- **Dynamic Security Settings**: Security values (max attempts, block time, etc) are now loaded from config, not hardcoded.
- **Improved Error Messaging**: On door open failure, users are prompted with 'Please contact the administrator.'
- **Documentation**: README and config.ini.example updated for new security features.
- **UI/JS Polish**: Minor bugfixes and cleanup for keypad and error handling.
- **Version bump to 1.6.0**

---

## v[1.5.0] - 2025-09-04

### 🛠️ Maintenance & Release Preparation
- Removed deprecated `repository.json` file.
- Moved `favicon-192.png` into the `static/` directory for better asset organization.
- Updated documentation and project structure to clarify Home Assistant add-on compatibility and standalone usage requirements.
- General code review and preparation for v1.5 release.

---

## v[1.4.0] - 2025-09-03

### 🆙 Dependency Updates
- Updated all core dependencies to latest stable versions (Flask 3.1.2, requests 2.32.5, Werkzeug 3.1.3, pytz 2025.2) for improved security and compatibility.

### ♻️ Maintenance
- General codebase maintenance and preparation for future features.

---

# Changelog

## v[1.3.0] - 2025-09-03

### 🚀 Features & Improvements
- Now you do not have to build anymore - ghcr setup!
### 🐛 Bug Fixes
- api error

---

## v[1.2.0] - 2025-09-02

### 🔒 Enhanced Security Features

#### ✨ New Security Improvements
- **Multi-Layer Rate Limiting** - Session-based (3 attempts), IP-based (5 attempts), and global (50/hour) protection
- **Enhanced IP Detection** - Uses `request.remote_addr` instead of spoofable client headers
- **Session Tracking** - Unique session identifiers prevent easy bypass of rate limits
- **Suspicious Request Detection** - Blocks requests with missing/bot User-Agent headers
- **Composite Identifiers** - IP + User-Agent/language fingerprinting for better tracking

#### 🎨 Visual Interface Improvements
- **Visual Keypad Interface** - Replaced text input with responsive 3x4 grid keypad (0-9, backspace, enter)
- **Auto-Submit PIN Entry** - Door opens automatically when valid PIN length (4-8 digits) is entered
- **Perfect Alignment** - PIN display and keypad visually centered and width-matched
- **Keyboard Support** - Physical keyboard input (0-9, Backspace, Enter) works alongside touch

#### 🔊 Audio & Feedback Features
- **Success Sound** - Ascending chime sequence using Web Audio API
- **Failure Sound** - "Womp womp" descending trombone effect for invalid attempts
- **Visual Feedback** - Button animations, haptic vibration, toast notifications
- **Responsive Design** - Optimized for both desktop and mobile devices

#### 🧪 Testing & Development
- **Test Mode** - Safe testing without physical door operation (`test_mode = true` in config.ini)
- **Simulated Success** - Shows success messages and logs without Home Assistant API calls
- **Full Feature Testing** - All keypad, audio, and security features work in test mode

#### 🌍 Timezone Support
- **Environment Variable** - Set `TZ` environment variable for local timezone (default: UTC)
- **Consistent Logging** - All timestamps in logs use the configured timezone
- **Docker Integration** - Timezone configuration through docker-compose environment

#### 🛠️ Technical Improvements
- **Enhanced Logging** - Session IDs, composite identifiers, and detailed status tracking
- **Progressive Security** - Multiple blocking mechanisms with different thresholds
- **Dependency Updates** - Added pytz for robust timezone handling

#### 🐛 Bug Fixes
- Fixed variable reference errors in logging statements
- Resolved import conflicts with configparser
- Improved error handling in security functions

---

## [1.1.0] - 2025-09-02

### 🔧 Configuration Improvements

#### ✨ New Features
- **Environment Variable Port Configuration** - Port can now be configured via `DOOROPENER_PORT` environment variable
- **Flexible Configuration Priority** - Environment variables take precedence over config.ini settings
- **Docker Environment Integration** - Seamless port configuration through .env files and docker-compose

#### 🛠️ Technical Improvements
- **Simplified Docker Setup** - Removed complex startup scripts in favor of environment variable approach
- **Better Configuration Management** - Clear priority order: ENV var → config.ini → default fallback
- **Enhanced Documentation** - Updated README with environment variable best practices

#### 📝 Configuration Priority Order
1. `DOOROPENER_PORT` environment variable (highest priority)
2. `config.ini` `[server]` `port` setting
3. Default fallback: 6532

#### 🐛 Bug Fixes
- Fixed Docker container not respecting config.ini port settings
- Improved port configuration consistency between host and container

---

## [1.0.0] - 2025-09-02

### 🎉 Initial Release

#### ✨ Features
- **Modern Glass Morphism UI** - Premium frosted glass interface with backdrop blur effects
- **Per-User PIN Authentication** - Individual PINs for each resident/user
- **Zigbee Device Integration** - Automatic device detection and real-time battery monitoring
- **Admin Dashboard** - Password-protected admin panel with audit logging
- **Rate Limiting & Security** - Per-IP progressive delays and brute-force protection
- **Docker Containerization** - Complete Docker setup with health checks and resource limits
- **Responsive Design** - Optimized for desktop, tablet, and mobile devices

#### 🔐 Security Features
- Per-IP rate limiting with progressive delays (1s, 2s, 4s, 8s, 16s)
- 5-minute IP lockout after 5 failed attempts
- Secure session management with HTTPOnly cookies
- Input validation and sanitization
- Comprehensive audit logging

#### 🔧 Technical Features
- Home Assistant API integration
- MQTT battery level monitoring
- Real-time status updates
- Custom background image support
- Haptic feedback on mobile devices
- Toast notifications for user feedback

#### 📱 User Interface
- Glass morphism design with backdrop filters
- Color-coded battery indicators
- Interactive button states with animations
- Mobile-optimized touch interface
- Admin access via floating gear icon

#### 🐳 Docker Support
- Multi-stage Docker build
- Health checks and restart policies
- Resource limits (0.5 CPU cores, 256MB RAM)
- Log rotation and volume mounts
- Environment-based configuration

### 🐛 Known Issues
- Admin login persistence: Sessions don't persist across page refreshes
- SESSION_COOKIE_SECURE set to False for local HTTP development

### 🔧 Configuration
- Supports any Home Assistant switch entity
- Configurable user PINs via config.ini
- Customizable admin password
- Environment variable support for secrets
