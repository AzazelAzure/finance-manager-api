# Changelog: Finance Manager API

All notable changes to the API codebase must be documented in this file by the executing agent. This provides context to other agents and prevents conflicting work.

## [Unreleased]
### Security & Configuration
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
