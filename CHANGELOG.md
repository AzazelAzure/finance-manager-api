# Changelog: Finance Manager API

All notable changes to the API codebase must be documented in this file by the executing agent. This provides context to other agents and prevents conflicting work.

## [Unreleased]
### Added
- **CI pipeline (PLAN_CROSS_CI_CD):** `.github/workflows/api-ci.yml` runs `pytest` and a `makemigrations --check --dry-run` migration drift gate on every push and PR to `main`. Dependencies install via `uv sync --frozen` on Python 3.12; tests use the SQLite fallback (no DB env vars) with a Redis service container (required by `ObservabilityMiddleware` + DRF throttling) and a pre-test `update_conversion_file` step that fetches the gitignored ECB exchange-rate data the currency converter needs. Added `.github/dependabot.yml` for weekly `uv` + `github-actions` update PRs.
- **Signup clickwrap (PLAN_CROSS_SIGNUP_CLICKWRAP):** `AppProfile.tos_version` and `tos_accepted_at` fields; registration requires both on account creation.
- **Support confirmation emails (PLAN_CROSS_EMAIL_COMMS):** `send_user_support_confirmation` Celery task sends user-facing confirmation after bug report or feature request submission. Five-minute per-user per-type cooldown skips duplicate confirmations; operator notify unchanged.
- **`create_ux_testuser` management command (PLAN_CROSS_UI_UX_TEST_SEED):** Seeds deterministic `ux_demo` user with 12 months of rolling PHP transaction history, categories, payment sources, tags, and upcoming expenses. Supports `--reset`, `--confirm-not-prod` (required when `DEBUG=False`), and configurable username/email/password.
- **Celery observability (T02–T04):** PII-safe `ObservabilityMiddleware` increments Redis traffic (`fm_metrics:*`) and security (`fm_security:*`) counters with normalized endpoints, salted IP hashes, and UA classification. Hourly `rollup_metrics_hourly`, daily `rollup_daily`, and weekly `rollup_weekly` Celery tasks write flat JSON analytics under `ANALYTICS_LOG_DIR` (default `/var/log/fm_api/analytics/`). `check_security_thresholds` beat task (every 15 min) fires `SECURITY_PROBE_DETECTED` operator alerts with cache dedup. Settings: `LOG_IP_HASH_SALT`, `ANALYTICS_LOG_DIR`, `SECURITY_ALERT_THRESHOLDS`, Redis-backed `CACHES`.
  - **Hardening (security review #39):** every `fm_metrics:*` key component is now bounded so the keyspace (enumerated by rollup/alert jobs with Redis `KEYS`) cannot be flooded by unauthenticated input — metrics are keyed on the resolved URL **route pattern** (e.g. `/finance/transactions/<str:tx_id>/`) with unresolved paths collapsed into a single `{unmatched}` bucket, and HTTP methods are bucketed against a fixed allowlist (unknown verbs → `OTHER`). Forwarded client-IP headers (`CF-Connecting-IP` / `X-Forwarded-For`) are ignored unless `OBSERVABILITY_TRUST_PROXY_IP=1`, preventing spoofed IPs from evading per-IP security thresholds.
- **F-014 usage monitoring + operator notify:** `notify_operator` Celery task with `[FM-NOTIFY]` email contract (UUID-only, no PII). Proton/SMTP settings via `EMAIL_*` env vars. `DailyUsageSnapshot`, `InviteChainEvent`, and `OperatorAlertState` models. Daily usage rollup beat task (UTC 00:05) with DAU threshold alerts (configurable via `DAU_ALERT_THRESHOLDS`). Bug reports now enqueue async operator notify instead of synchronous email with username/email in body.
- **F-012/F-013 verification hardening:** Support text secret redaction (`Bearer`, `password=` patterns). Weekly feature digest filters last **7 days** + `emailed=False`. F-013 verification tests (anonymous/forged uid, feature ticket skips incident dump).

### Fixed
- **Production UX (PLAN_CROSS_PRODUCTION_UX_FIX, T02):** Bill linking via transaction `bill` field marks one-time upcoming expenses paid; recurring bills advance `due_date` by bill interval (monthly fallback when interval unknown). Added `POST /finance/upcoming_expenses/<name>/catch-up/` for overdue mark-paid-and-advance (max 24 periods). See `strategy/anomalies/2026-06-28_PRODUCTION-UX-FIX_T02_bill-interval-cycle-revamp.md` for follow-up recurrence-engine work.
- **Test suite determinism (PLAN_CROSS_CI_CD):** Added `conftest.py` that seeds `random`, `factory.random`, and `Faker` before each test (override with `FM_TEST_SEED`), so the suite no longer depends on the process's random state. Made the two currency-sensitive transaction tests stable regardless of the random draw: the calendar month-boundary test forces its source onto the profile base currency (a randomly assigned weak currency could round a -100 expense to 0.00), and the safe-to-spend snapshot test posts its trigger expense to a non-spend source in the base currency (the random expense could otherwise perturb the spend-account balance). Verified green across 5 seeds.
- **Stale tests surfaced by CI (PLAN_CROSS_CI_CD):** Updated three tests that no longer matched shipped behavior and failed once CI ran them with Redis available. `test_permission_defaults.py` user-creation tests now send the `tos_version` / `tos_accepted_at` fields required since the ToS clickwrap (PR #42). `test_support_adversarial.py::test_parameter_injection_spoofing_uid` now asserts `emailed=True` for BUG tickets: `emailed` is read-only on the serializer (so the client-supplied value is still ignored — the anti-spoof guarantee is intact), and the view sets it `True` after dispatching the operator notification (F-012/F-014).
- **Signup clickwrap bypass (PR #42 review):** The public `POST /api/auth/registration/` (dj-rest-auth) route used `EmailUniqueRegisterSerializer`, which neither required nor persisted ToS fields, so an unauthenticated client could create an account with no recorded ToS acceptance (the `post_save` AppProfile signal left `tos_version`/`tos_accepted_at` null). The registration serializer now requires a supported `tos_version` plus `tos_accepted_at` and records acceptance with a server-set timestamp via `custom_signup`. Shared `finance.api_tools.tos` helper (`ALLOWED_TOS_VERSIONS`, `record_tos_acceptance`) now backs both the `/finance/user/` clickwrap path and the public registration path; the client-supplied timestamp is never trusted. Added registration tests covering rejection without acceptance, unsupported-version rejection, and server-set-timestamp persistence.
- **Celery task autodiscovery (F-014):** Added `finance/tasks/__init__.py` so `autodiscover_tasks` imports the task submodules. Previously `finance.tasks` was a namespace package, so only `notify_operator` (imported by the support view) was registered; beat-scheduled `rollup_daily_usage` and `send_weekly_feature_requests_email` were never registered and would be discarded by the worker as unregistered tasks. Adds a regression test asserting every `CELERY_BEAT_SCHEDULE` task is registered.
- **Weekly feature digest HTML escaping:** Escapes user-submitted support ticket fields before building the operator HTML digest, preventing stored HTML/phishing markup from FEATURE tickets from rendering in the operator email client.

### Changed
- **F-012 bug notify path:** `SupportTicketView` incident dump extracted to `finance.services.support_incident`; operator email moved to F-014 `notify_operator.delay()` (submission no longer fails on SMTP errors in request thread).
- **F-014 feature-request notify:** FEATURE tickets now enqueue `notify_operator` with `FEATURE_REQUEST` event type (real-time, same as bugs).
- **Celery observability T01 (FROM routing):** `notify_operator` sends FROM `bugreport@`, `featurerequest@`, or `noreply@thehivemanager.com` per event type via `get_notify_from_address()`.

### Added (security — merged PR #35/#36)
- **Support Ticket Comment Length & Digest Task Alignment (F-012):** Restricted support ticket serializer comment field to a maximum length of 5000 characters to prevent memory exhaustion/DoS. Re-aligned the Celery `send_weekly_feature_requests_email` task to query only features where `emailed=False`, limit to 100 tickets, and update them atomically in a transaction after email delivery. Configured Celery beat schedule to run every Monday at 9:00 AM.
- **AppProfile Completed Tours (F-007):** Added `completed_tours` JSON field to `AppProfile` model and exposed it in profile serializers to persist UI Guided Walkthrough state across devices.
- **Offline PWA exchange matrix:** `GET /finance/exchange_rates/?currencies=USD,PHP,...` (auth required) returns pairwise factors `convert_currency(Decimal("1"), from, to)` for up to 24 codes so the web client can persist a **minimal** rate table (profile base + sources + cached tx currencies) for offline conversion aligned with transaction math.

- **PWA D2 writes (idempotency + client build):** New `IdempotencyRecord` model and `PwaWriteContractMiddleware` for v1 allowlisted mutators (`POST/PATCH/DELETE` transactions; `POST/PATCH/PUT/DELETE` upcoming expenses). Optional `Idempotency-Key` enables duplicate-safe replay; keys on non-allowlisted `/finance/*` mutators return **400** (`IDEMPOTENCY_SCOPE`). Optional `CLIENT_BUILD_MIN_WRITE` enforces `X-Client-Build` on `/finance/*` mutations with standardized **409** JSON (`CLIENT_BUILD_UNSUPPORTED`). `GET /api/health/` now returns `api_server_build` and `min_client_build_write`. `DELETE` on a missing transaction with `Idempotency-Key` can return **200** `{"idempotent": true, "tx_id": "..."}` for outbox alignment.

### Changed
- **PWA D2 idempotency allowlist (app profile):** `PATCH /finance/appprofile/` is now on the **`PwaWriteContractMiddleware`** allowlist so **`Idempotency-Key`** is accepted and **duplicate-safe replay** applies to offline-queued profile saves (same `IdempotencyRecord` retention as other allowlisted mutators).
- **PWA D2 idempotency allowlist (lookup mutations):** `Idempotency-Key` is now accepted for **categories**, **tags**, and **sources** mutators (`POST /finance/categories/`, `PATCH|DELETE /finance/categories/{name}/`, `POST|PATCH|DELETE /finance/tags/`, `POST /finance/sources/`, `PATCH|DELETE /finance/sources/{source}/`) so outbox replay after offline Quick add (category then transaction) does not fail with **400** `IDEMPOTENCY_SCOPE`.
- **Email uniqueness (S0):** PostgreSQL gets a case-insensitive unique index on `LOWER(auth_user.email)` (`finance.0005_auth_user_email_ci_unique`). `POST /finance/user/` returns field-level `400` errors for duplicate username or email; `dj-rest-auth` registration uses `EmailUniqueRegisterSerializer` so `POST /api/auth/registration/` rejects duplicate emails case-insensitively before insert.

### Documentation

- **PWA sprint CPPRD cross-link:** No additional API code in the web PWA UI batch; contract remains the **[Unreleased] PWA D2 writes** item above. D4-exec evidence and breakpoint status are tracked in the ecosystem parent workspace under `plans/S1/S1.B/pwa-implementation-branch/` (`evidence/`, `validation_gates.md`).

### Fixed
- **CORS preflight for PWA custom headers:** `CORS_ALLOW_HEADERS` now extends `django-cors-headers` defaults with `x-client-build` and `idempotency-key` so browser preflight (`OPTIONS`) on cross-origin mutating requests succeeds. Without this, every `POST`/`PATCH`/`DELETE` from the SPA to `api.thehivemanager.com` was silently blocked because `X-Client-Build` (added in T03) is a non-simple header not in the library's default allowlist.
- **PATCH transaction + source balances:** `update_transaction` now passes **`prior_for_reversal`** (bill, source, amount, currency, date captured **before** applying the patch) into `transaction_handler(update=...)`. Previously the ORM row was saved with new values first, so `_handle_tx_update` reversed the **new** row instead of the old one and `PaymentSource.amount` drifted on amount/source/currency/type edits.
- **Transaction delete + source balances (KNOWN_ISSUES #8):** `_handle_tx_update` now **reverses the same currency-adjusted delta** that `calc_tx_sources` applies when a row is created, so deleting a cross-currency transaction no longer corrupts `PaymentSource.amount`. After the row is removed, `source_handler` runs so snapshot metrics (e.g. transfers, monthly spend) do not still reference the deleted transaction.

- **Upcoming expense edit recurring toggle:** `PATCH /finance/upcoming_expenses/{name}/` now accepts `recurring_flag` as a compatibility alias and maps it to canonical `is_recurring`, preventing recurring-bill edit failures from clients still sending the legacy field key.
- **Snapshot KPIs (safe to spend + remaining expenses):** `Updater._tx_snapshot_handler` used only **recurring** upcoming bills for `safe_to_spend` while `total_remaining_expenses` counted **all** unpaid bills due in the profile’s current month, which made the two KPIs inconsistent and could inflate safe-to-spend. Both fields now use the same bill set: unpaid with `due_date` in the profile timezone’s current month. `expense_handler` / `source_handler` / `user_handler` use the same month boundaries (profile TZ) instead of `get_current_month()` on server local date.
- **App profile snapshot (no `FinancialSnapshot` row):** `GET /finance/appprofile/snapshot/` can return `snapshot: null` for users who have not yet got a stored snapshot. The snapshot response serializer now allows a null nested `snapshot` so the endpoint returns `200` with computed totals and empty series instead of failing during serialization (which surfaced to the Reflex dashboard as a failed API request after login).

### Security & Configuration
- **Auth hardening (S1.B):** Argon2 is the default password hasher; minimum password length is 12 with a custom complexity validator (mixed case, number, special character). `PATCH /finance/user/` password changes now run Django `validate_password` before `set_password`. **django-axes** adds login lockout after repeated failures (`migrate axes` required on deploy). HSTS sub-domain/preload flags follow `SECURE_HSTS_SECONDS` (env override or auto when `SECURE_SSL_REDIRECT` is on). Nginx client IP for axes uses `AXES_IPWARE_PROXY_COUNT` (default `1`).
- **CORS middleware order:** `CorsMiddleware` is now first in `MIDDLEWARE` (per django-cors-headers guidance). Added [docs/CORS_PRODUCTION_TROUBLESHOOTING.md](docs/CORS_PRODUCTION_TROUBLESHOOTING.md) for **ERR_NETWORK** / empty preflight when the public `api` hostname differs from direct-to-box tests (often **Cloudflare cache** on OPTIONS).
- **CORS dependency**: Declared `django-cors-headers` in `pyproject.toml` / `uv.lock` so `corsheaders` installs in CI and container images (middleware was already wired in settings).
- **Web beta CORS/CSRF defaults**: Default `CORS_ALLOWED_ORIGINS` now includes Vite dev (`http://localhost:5173`, `http://127.0.0.1:5173`), `https://jsdevtesting.thehivemanager.com`, and `https://api-jsdevtesting.thehivemanager.com` (aligned with Nginx staging API hostname and tunnel naming). Default `CSRF_TRUSTED_ORIGINS` includes those origins plus the production hive hosts; staging API is `https://api-jsdevtesting.thehivemanager.com` (inactive `api-*` behind Nginx). Deployments can still override via `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` env; ensure `ALLOWED_HOSTS` includes the staging API hostname.
- **Production settings parsing**: `DEBUG` and boolean deployment flags (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`) now use explicit environment boolean parsing so `DEBUG=False` is not misread as true.
- **HSTS policy flags**: Added env-driven `SECURE_HSTS_INCLUDE_SUBDOMAINS` and `SECURE_HSTS_PRELOAD` so deploy-check warnings `W005`/`W021` can be explicitly enabled for beta/prod domains.
- **TLS-related settings**: Optional HTTPS/cookie hardening can be enabled per environment for beta and `manage.py check --deploy` runs. Residual HSTS sub-domain/preload warnings (W005, W021) may remain until the public domain and proxy policy are fixed.
- **Secret hygiene**: Removed tracked `.env.bak`; `.gitignore` now covers `.env*` and `*.bak`; added `.env.example`. **Rotate** any credentials ever present in removed env backups (out of band).
- **Log privacy defaults**: Request log context uses `username=authenticated` unless `LOG_FULL_USERNAME=1`. Transaction validation and several service/validator logs use key previews instead of raw payloads or user-entered values; see `finance/api_tools/redaction.py`.

### Tests
- **Pytest collection scope**: `pytest.ini` now sets `testpaths = finance/tests` so ad-hoc root-level helper scripts are not collected as tests.
- **URL reverse names**: Aligned `urlpatterns` names with integration tests for categories, upcoming expenses, and source detail routes; source delete and stress tests use detail-route DELETE; profile method-denial tests expect `405` for unsupported HTTP methods on `AppProfileView`.

### Features
- **Visualization Aggregate Packets**: Added `GET /finance/transactions/visualization/` to return chart-ready transaction flow/type/category aggregates plus upcoming-expense timeline/monthly/status packets for a date range.
- **Upcoming Expense PATCH Alias**: Added partial-update compatibility for `PATCH /finance/upcoming-expenses/{name}/` requests that send `{"paid": true}` by mapping the alias to the canonical `paid_flag` field.
- **Calendar Contract Freeze (Phase 1)**: Expanded `GET /finance/transactions/calendar/` with explicit `base_currency`, `display_currency_mode`, `heat_metric_mode`, `heat_max`, per-day `heat_value`/`heat_intensity`, and `due_events` overlays while keeping daily/weekly/monthly aggregates base-currency normalized.
- **Refresh Missing-User Hardening**: Wrapped JWT refresh serializer validation paths so refresh tokens that reference deleted users now return `401` InvalidToken responses instead of `500` server errors.

### Tests
- **Visualization Contract Coverage**: Added aggregate correctness tests for mixed transaction types and paid/unpaid upcoming expense summaries.
- **Calendar Contract Coverage**: Added assertions for heatmap metadata, due-event overlays, and display/heat mode query semantics in the transactions calendar response.
- **Dashboard Snapshot Contract Coverage**: Added profile snapshot assertions that enforce `expense_by_category` and `source_balances` dashboard-support fields in the snapshot payload.
- **Expense PATCH Alias Coverage**: Added integration coverage confirming `paid` alias updates `paid_flag` in upcoming expense partial updates.
- **Transaction Serializer Contract Coverage**: Added deterministic serializer-level checks confirming transaction payload Decimal parsing and tag-list acceptance for quick-entry compatible request shapes.
- **Dashboard Series Contract Coverage**: Added snapshot assertions for `flow_series`, `daily_spend`, and `daily_income` to protect dashboard chart-support payload shape.
- **Transaction Serializer Optional-Field Coverage**: Added serializer-level checks that transaction payloads accept Decimal/tag data and optional category + nullable bill fields for quick-entry compatibility.
- **Refresh Resilience Coverage**: Added regression coverage for both `/api/token/refresh/` and `/api/auth/token/refresh/` to ensure deleted-user refresh tokens fail with auth errors rather than 500s.

### Documentation
- **README Version Clarification**: Clarified `README.md` to distinguish current code version from public release status for private-repo visibility.

## [v1.2.1] - 2026-04-27
### Features
- **Bug Report Pipeline Baseline**: Added authenticated `POST /finance/bug-report/` support with configurable email routing (`BUG_REPORT_TO_EMAIL`) and integration coverage.

### Security & Contracts
- **JWT Verify Contract Fix**: Corrected `/api/token/verify/` routing to use `TokenVerifyView` instead of refresh behavior.

### Observability
- **User-Tagged Logging Baseline**: Added request-scoped log context (`uid`, `username`) and default Loguru extras for per-user operational tracing.

### Tests
- **Phase 2 API Gate Coverage**: Added targeted tests for token verify route binding and bug report email dispatch.

## [v1.2.0] - 2026-04-26
### Features
- **REST View Split**: Fully refactored combined resource views into standard `ListCreateView` and `DetailView` patterns for Transactions, Categories, Sources, and Upcoming Expenses.
- **Data Ordering**: Implemented descending chronological sorting (`-date, -tx_id`) as the default for all transaction list retrievals and dashboard totals.

### Bug Fixes
- **Validation**: Updated `tx_serializers.py` to allow `blank=True` and `null=True` on the `bill` field, resolving 400 Bad Request errors.
- **Expenses Fix**: Corrected boolean interpretation for `paid_flag` and `recurring` filters in `UpcomingExpense` services to prevent 500 errors from string query parameters.
- **Schema Stability**: Implemented an explicit `ref_name` monkeypatch for `TokenRefreshSerializer` and `CookieTokenRefreshSerializer` within `finance/apps.py` (`ready()`) to resolve persistent naming collisions between SimpleJWT and DjRestAuth without causing circular imports during boot.

## [v1.1.0] - 2026-04-26
### Documentation
- **Comprehensive API Documentation**: Created detailed documentation in `design_docs/api_docs/`, covering Architecture, Endpoints, Models, Business Logic, Security, Data Access, and Tools.

### Security & Hardening
- **Auth Security**: Updated JWT configuration to extend session lifetimes (Access: 1 day, Refresh: 7 days) for improved user convenience.
- **Security Hardening**: Enhanced `UserView` to require password verification for account updates and deletion.
- **Data Privacy**: Hardened account deletion signals to ensure complete wipes of all financial data.

### Bug Fixes
- **Signal Resilience**: Fixed `AppProfile` creation signal to skip during fixture loading, preventing migration errors.

## [v1.0.4] - 2026-04-25
### Features
- **Dashboard API**: Enhanced payload to include live `source_balances` and Recharts-compatible `expense_by_category` format.
- **Transaction Aggregates**: Added month-to-date category aggregates to transaction serializers.
- **Improved Defaults**: Refactored `get_transactions` to return the current month by default.
- **Visibility**: Included `XFER_OUT` in category breakdowns for better financial oversight.

## [v1.0.0] - 2026-04-25
### Initial MVP Release
- **Core Architecture**: Established 6-layer architecture with Django REST Framework.
- **OAuth2 Integration**: Implemented Google and GitHub social login using `dj-rest-auth`.
- **Dockerized Environment**: Optimized Dockerfile with `uv sync` and PostgreSQL support.
- **Environment Stability**: Configured HTTPS simulation, CSRF trusted origins, and SELinux support.
- **Tooling**: Added management scripts for services, Docker, and database migrations.
- **Shell Integration**: Added productivity aliases for service and container management.
- **Bug Fixes**: Resolved `psycopg` compatibility for Python 3.14.
