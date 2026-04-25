# Changelog: Finance Manager API

All notable changes to the API codebase must be documented in this file by the executing agent. This provides context to other agents and prevents conflicting work.

## [Unreleased]
- Setup initial `CHANGELOG.md` to track agent modifications.
- Upgraded Dockerfile to use `uv sync`.
- Added `psycopg[binary]` for PostgreSQL support.
- Configured HTTPS simulation (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).
- Added internal service name `api` to `ALLOWED_HOSTS` in Docker Compose for secure Reflex-to-Django internal routing.
- Configured CSRF_TRUSTED_ORIGINS to support non-privileged port 8443 for Rootless Podman compatibility.
- Added `:z` SELinux flag to certificate volume mounts in Docker Compose to resolve Fedora access denials.
- Added service management script `scripts/fm_services.sh` for local execution.
- Added Docker management script `scripts/fm_docker.sh` (with podman-compose support).
- Added `scripts/setup_db_creds.sh` for automated DB password generation and .env configuration.
- Added shell aliases: `fm-mount`, `fm-restart`, `fm-stopservice`, `fmdock-mount`, `fmdock-restart`, `fmdock-stopservice`, and `fm-setdbcreds`.
- Added `expense_by_category` to `TransactionGetReturnSerializer` and updated `get_transactions` service to return month-to-date category aggregates.
- Refactored `get_transactions` default behavior to return the current month's transactions when no filters are provided, improving dashboard default state.
- Updated `user_get_totals` to include `XFER_OUT` in category breakdown for more comprehensive financial visibility.
- **Roadmap Refinement:** Clarified Phase 2 (Beta) goals and established the "Dual-Track Development" strategy for Phase 3 (Post-Beta). Zero-Knowledge implementation confirmed as a long-term goal well after initial Beta.
- **Auth Hardening:** Implemented OAuth2 integration using `dj-rest-auth` and `django-allauth`. Added Google and GitHub social login endpoints with JWT bridge support.
- **Environment Stability:** Fixed `psycopg` dependency to support Python 3.14 by switching to pure-python fallback mode (avoiding missing binary wheels).
- **Architecture:** Created `finance/views/auth_views.py` to centralize social login logic and updated `urls.py` with comprehensive auth routing.
- **Security Hardening:** Updated `UserView` to require current password verification for both password updates and account deletion, mitigating unauthorized takeover and accidental data loss.
- **Data Privacy:** Hardened account deletion signals to ensure a complete wipe of all financial data (transactions, sources, categories, etc.) upon user deletion.
- **Migration Tooling:** Optimized `scripts/db_migrate.sh` and related utilities for `uv` environment compatibility and more robust PostgreSQL connection checking.
- **Signal Resilience:** Fixed `AppProfile` creation signal to skip during fixture loading (raw=True), preventing `IntegrityError` during DB migrations.
- **Dashboard API:** Enhanced the dashboard payload (`AppProfileView.get(snapshot=True)`) to include live `source_balances` and refactored `expense_by_category` into a list-of-dicts format for direct Recharts compatibility.
- **Auth Security:** Updated JWT configuration to extend session lifetimes. Access tokens now last 1 day and Refresh tokens last 7 days, balancing user convenience with security best practices.
