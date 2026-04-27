# Changelog: Finance Manager API

All notable changes to the API codebase must be documented in this file by the executing agent. This provides context to other agents and prevents conflicting work.

## [Unreleased]
### Features
- **Visualization Aggregate Packets**: Added `GET /finance/transactions/visualization/` to return chart-ready transaction flow/type/category aggregates plus upcoming-expense timeline/monthly/status packets for a date range.
- **Upcoming Expense PATCH Alias**: Added partial-update compatibility for `PATCH /finance/upcoming-expenses/{name}/` requests that send `{"paid": true}` by mapping the alias to the canonical `paid_flag` field.

### Tests
- **Visualization Contract Coverage**: Added aggregate correctness tests for mixed transaction types and paid/unpaid upcoming expense summaries.
- **Dashboard Snapshot Contract Coverage**: Added profile snapshot assertions that enforce `expense_by_category` and `source_balances` dashboard-support fields in the snapshot payload.
- **Expense PATCH Alias Coverage**: Added integration coverage confirming `paid` alias updates `paid_flag` in upcoming expense partial updates.
- **Dashboard Series Contract Coverage**: Added snapshot assertions for `flow_series`, `daily_spend`, and `daily_income` to protect dashboard chart-support payload shape.

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
