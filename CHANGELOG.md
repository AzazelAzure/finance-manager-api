# Changelog: Finance Manager API

All notable changes to the API codebase must be documented in this file by the executing agent. This provides context to other agents and prevents conflicting work.

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
