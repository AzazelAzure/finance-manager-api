# Finance Manager API (Django + DRF)

A multi-endpoint API for managing financial data: transactions, payment sources, upcoming expenses, categories, tags, and user app-profile totals/snapshots. The project also includes automated tests, API documentation (OpenAPI/Swagger), and an MVP-focused Docker setup.

## Features

- REST API with JWT authentication
- Domain-layer separation:
  - Views: thin request/response layer
  - Validators: request validation and payload normalization
  - Services: orchestration of CRUD + dependent recalculation
  - Updaters/Calculator: financial side-effects and totals computation
- Automated test suite (pytest) + coverage
- Swagger/OpenAPI docs via `drf-spectacular`
- Dockerfile to containerize the app for local runs
- Request DB-hit instrumentation (dev/debug profiling)

## Tech Stack

- Django 6.0.x
- Django REST Framework
- drf-spectacular (OpenAPI + Swagger UI)
- djangorestframework-simplejwt (JWT auth)
- pytest + pytest-django + coverage
- Optional PostgreSQL for concurrency / load testing

## Requirements

- Python (recommended: 3.12+)
- Currency conversion archive: `finance/data/exchange_rates.zip` (handled by setup commands)
- Environment variables (at minimum):
  - `SECRET_KEY`
  - `DEBUG` (string values like `"true"` enable dev instrumentation)
  - Optional DB env vars if using PostgreSQL:
    - `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

## Setup (Development / Local)

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
