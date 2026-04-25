# Finance Manager API

Backend API for a personal finance/budgeting workflow: manage payment sources, upcoming expenses, categories, tags, and transactions, and retrieve a computed financial snapshot in the user's base currency.

This project is designed for clean multi-user isolation (per-user data partitioning) and "financial fidelity" (immutable transaction identity, controlled update semantics, and consistent recalculation of balances/snapshots after mutations).

## Quick Links

- API documentation (Swagger UI): `/api/docs/`
- OpenAPI schema: `/api/schema/`
- JWT token endpoints:
  - Obtain access/refresh token pair: `/api/token/`
  - Refresh: `/api/token/refresh/`
  - Verify/other SimpleJWT helpers are also wired (see `finance_api/urls.py`).

## Features

### Per-user data isolation

- Users are authenticated with JWT.
- A user-linked `AppProfile` is automatically created on user signup (via model signals).
- Domain objects (transactions, sources, upcoming expenses, categories, tags, snapshots) are stored per user using a profile `user_id`/`uid`.

### Financial fidelity rules (important)

- Transaction identity fields are immutable:
  - `PUT /finance/transactions/<tx_id>/` is disabled (returns `405`).
  - `PATCH /finance/transactions/<tx_id>/` rejects client-supplied `tx_id` and `entry_id`.
  - Transaction updates require a `date` field.
- The reserved payment source name `unknown`:
  - Is created automatically for each user.
  - Cannot be modified/deleted via the Sources endpoints.
  - When a source is deleted, any transactions referencing it are remapped to `unknown` to preserve integrity.

### Automatic snapshot recalculation

- A `FinancialSnapshot` is maintained for each user.
- Snapshot totals are computed in the user's `base_currency`.
- After relevant mutations (sources/transactions/expenses/profile), totals and derived values (safe-to-spend, assets, leaks) are recomputed via a calculation "Calculator" + "Updater" flow.

### Currency conversion

- Currency conversion uses an ECB daily exchange-rate archive stored at:
  - `finance/data/exchange_rates.zip`
- If the exchange rate archive is missing, currency conversion fails (no silent fallback).
- A management command is provided to download/update the archive:
  - `python manage.py update_conversion_file`

## Tech Stack

- Python 3.12+
- Django 6.0.1
- Django REST Framework (DRF)
- `djangorestframework-simplejwt` (JWT auth)
- `drf-spectacular` (OpenAPI schema generation + Swagger UI)
- `loguru` (logging)
- `currency_converter` / `CurrencyConverter` (ECB exchange rates)

## Requirements

Runtime deps:

```bash
pip install -r requirements-prod.txt
```

Test deps:

```bash
pip install -r requirements-test.txt
```

## Configuration

Django loads environment variables from `.env` (via `python-dotenv`).

### Required

- `SECRET_KEY` (required)

### Optional

- `DEBUG` (controls debug behavior; also toggles DB hit logging middleware output)
- `ALLOWED_HOSTS` (comma-separated; default `"*"`)

### Database (optional; defaults to SQLite)

- `DB_ENGINE` (e.g. `django.db.backends.postgresql` / `postgres` / `postgresql`)
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST` (default `127.0.0.1`)
- `DB_PORT` (default `5432`)

## Setup & Run (Development)

### 1) Run migrations

```bash
python manage.py migrate
```

### 2) (Recommended) Ensure exchange rates are available

If `finance/data/exchange_rates.zip` is missing, run:

```bash
python manage.py update_conversion_file
```

### 3) Start the server

```bash
python manage.py runserver 0.0.0.0:8000
```

### Helpful management commands

The project includes schema/demo bootstrap commands:

- `prod_setup`
  - Validates exchange-rate setup
  - Applies migrations (unless `--no-migrate`)
  - Optionally collects static files (unless `--no-static`)
  - Optionally creates a superuser (via flags + env vars)
- `schema_setup`
  - Runs `prod_setup` prerequisites
  - Seeds demo users and finance data
  - Key flags:
    - `--users` (default: 1000)
    - `--transactions-per-user` (default: 1000)
    - `--categories-per-user` (default: 10)
    - `--tags-per-user` (default: 10)
    - `--sources-per-user` (default: 10)
    - `--upcoming-expenses-per-user` (default: 10)
    - `--batch-size` (default: 2000)
    - `--dry-run`
    - `--skip-conversion-download`

## Docker

The `Dockerfile` installs production dependencies and runs database migrations before starting the API.

Build:

```bash
docker build -t finance-manager-api .
```

Run:

```bash
docker run -p 8000:8000 -e PORT=8000 finance-manager-api
```

## Authentication (JWT)

The REST framework is configured to use `JWTAuthentication`.

SimpleJWT configuration:

- Access token lifetime: 10 minutes
- Refresh token lifetime: 1 day
- Refresh token rotation enabled
- Blacklist after rotation enabled

### Example: create a user + obtain a token

1. Create user:

```bash
curl -X POST http://localhost:8000/finance/user/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "user_email": "demo_user@example.com",
    "password": "ChangeMe123!"
  }'
```

2. Obtain tokens:

```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "ChangeMe123!"
  }'
```

3. Call an authenticated endpoint:

```bash
curl -X GET http://localhost:8000/finance/appprofile/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## API Endpoints

All finance endpoints are under `/finance/...`.

> Note: payload fields below reflect the DRF serializers implemented in `finance/api_tools/serializers/`.

### Transactions

- `POST /finance/transactions/`
  - Create one transaction or an array of transactions.
  - Notable behavior:
    - Client-supplied `tx_id` and `entry_id` are rejected.
    - Transaction amounts are normalized by type in services/updaters.
  - Payload fields (from `TransactionSetSerializer`):
    - `date` (optional on create; required for PATCH)
    - `description` (optional)
    - `amount` (required)
    - `source` (required)
    - `currency` (required; 3-letter code)
    - `tags` (optional; list of strings)
    - `tx_type` (required; e.g. `EXPENSE`, `INCOME`, `XFER_IN`, `XFER_OUT`)
    - `category` (optional)
    - `bill` (optional)
  - Returns: accepted/rejected/updated plus optional snapshot.

- `GET /finance/transactions/`
  - Retrieve transactions with optional filters via query parameters (see view docs), such as:
    - `tx_type`, `tag_name`, `category`, `source`, `currency_code`
    - date ranges: `start_date`, `end_date`, `date`, `gte`, `lte`
    - time windows: `current_month`, `month`, `year`, `last_month`, `previous_week`

- `GET /finance/transactions/<tx_id>/`
  - Retrieve a single transaction.

- `PATCH /finance/transactions/<tx_id>/`
  - Partially update a transaction identified by `tx_id`.
  - Requires `date` in the request body.
  - Rejects changes to identity fields (`tx_id`, `entry_id`).

- `DELETE /finance/transactions/<tx_id>/`
  - Delete a transaction identified by `tx_id`.

### Upcoming Expenses (Bills)

- `POST /finance/upcoming_expenses/`
  - Create one or more upcoming expenses.
  - Payload fields (from `ExpensePostSerializer`):
    - `name` (required)
    - `amount` (required)
    - `currency` (required)
    - `due_date`, `start_date`, `end_date` (optional)
    - `paid_flag` (optional)
    - `is_recurring` (optional)

- `GET /finance/upcoming_expenses/`
  - List upcoming expenses, with optional filters via query parameters (e.g. `remaining`, `recurring`, `paid_flag`, `for_month`, etc.).

- `PUT /finance/upcoming_expenses/<name>/`
  - Replace mutable fields for an existing expense.

- `PATCH /finance/upcoming_expenses/<name>/`
  - Partially update an expense.

- `DELETE /finance/upcoming_expenses/<name>/`
  - Delete an upcoming expense.

### Payment Sources

- `POST /finance/sources/`
  - Create one or more payment sources.
  - Reserved source name `unknown` is rejected by validation.

- `GET /finance/sources/`
  - List sources for the authenticated user.
  - Optional query filters include `acc_type` and `source`.

- `GET /finance/sources/<source>/`
  - Retrieve a single source.

- `PUT /finance/sources/<source>/`
  - Update mutable fields for an existing source.
  - `unknown` is not allowed to be modified.

- `PATCH /finance/sources/<source>/`
  - Partial update for a source.
  - `unknown` is not allowed to be modified.

- `DELETE /finance/sources/`
  - Deletes a source; the source name is provided in request body under `source`.
  - `unknown` cannot be deleted.

### Categories

- `POST /finance/categories/`
  - Create a category.
  - Payload: `{ "name": "<category_name>" }`

- `GET /finance/categories/`
  - List categories.

- `GET /finance/categories/<cat_name>/`
  - Retrieve a single category.

- `PUT /finance/categories/<cat_name>/`
  - Update/rename a category (by name).

- `PATCH /finance/categories/<cat_name>/`
  - Partially update/rename a category.

- `DELETE /finance/categories/<cat_name>/`
  - Delete a category.

### Tags

- `POST /finance/tags/`
  - Add one or more tags.
  - Payload: `{ "tags": ["groceries", "rent"] }` (case-insensitive; duplicates rejected).

- `GET /finance/tags/`
  - Retrieve tags list.

- `PATCH /finance/tags/`
  - Rename tags or delete tags via mapping object under `tags`:
    - Rename example: `{ "tags": { "oldTag": "newTag" } }`
    - Delete example: `{ "tags": { "obsoleteTag": null } }`
  - The service prevents "rename and delete in the same request".

- `PUT /finance/tags/`
  - Same payload format as PATCH.

- `DELETE /finance/tags/`
  - Same payload format as PATCH/PUT:
    - `{ "tags": { "obsoleteTag": null } }` to delete one or more tags.

## App Profile & Snapshot

- `GET /finance/appprofile/`
  - Returns profile configuration:
    - `spend_accounts` (list)
    - `base_currency` (3-letter code)
    - `timezone`
    - `start_of_week`

- `GET /finance/appprofile/snapshot/`
  - Returns computed dashboard totals (snapshot + transactions and aggregates for the current month).

- `PATCH /finance/appprofile/`
  - Update profile configuration (spend accounts/base currency/timezone and start-of-week).
  - Supported fields (from `user_services.user_update`):
    - `spend_accounts` (list or scalar; lowercased)
    - `base_currency` (3-letter code, uppercased)
    - `timezone`
    - `start_week` (maps to `start_of_week`)

## Testing & Stress Testing

### Unit/integration tests

Run:

```bash
pytest
```

The test suite uses `pytest-django` and the Django settings module `finance_api.settings` (see `pytest.ini`).

### Load/stress tests (Locust)

The repo includes stress/load testing with Locust plus deterministic seed data:

- `stress_tests/README.md` documents:
  - seeding users/data
  - running Locust profiles (`10, 50, 100, 250, 500, 1000` users)
  - baseline latency/error gates

## Project Layout (high-level)

- `finance_api/`: Django project (settings, URL routing, ASGI/WSGI).
- `finance/`: Django app (models, services, validators, serializers, API views, signals, management commands).
- `stress_tests/`: Locust scripts and data seeding helpers for load testing.

## Notes for Employers / Interviewers

- The API is organized around clear separation of concerns:
  - Views (HTTP + schema)
  - Serializers (payload validation)
  - Validators (domain constraints)
  - Services (read/write orchestration)
  - Updaters/Calculator (consistent recomputation after mutations)
- "Financial fidelity" is enforced at the API boundary and supported by service/update logic:
  - immutable transaction identifiers,
  - controlled updates,
  - and safe handling of deleted sources via an `unknown` remap.

## License

No license file was detected in this repository. Add one if you intend to publish this code externally.

