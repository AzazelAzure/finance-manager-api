# Stress Tests (Lane A)

This package provides API stress/load testing with Locust plus deterministic data seeding.

## Files

- `locustfile.py`: Locust entrypoint and summary gate writing.
- `user_flows.py`: weighted multi-user CRUD/read flows and contention tasks.
- `config.py`: run profiles (`10, 50, 100, 250, 500, 1000`) and baseline gates.
- `seed_data.py`: deterministic seed/reset utility for stress users and baseline rows.
- `results/`: output folder for summaries and raw artifacts.

## Prerequisites

Install Locust in your environment:

```bash
pip install locust
```

Ensure Django API server is running and reachable.

## Seed Users/Data

```bash
python stress_tests/seed_data.py --reset --count 1000
```

Defaults:
- username template: `stress_user_{N}`
- password: `StressPass123!`
- email domain: `example.com`

Override via flags (`--prefix`, `--password`, `--email-domain`).

## Run Profiles

Each profile maps to users/spawn/duration:

- `10`: sanity baseline
- `50`: low load
- `100`: medium
- `250`: heavy
- `500`: stress
- `1000`: upper bound

Examples:

```bash
locust -f stress_tests/locustfile.py --headless --host http://127.0.0.1:8000 -u 10 -r 2 -t 3m --seeded-users 1000 --password StressPass123!
locust -f stress_tests/locustfile.py --headless --host http://127.0.0.1:8000 -u 100 -r 10 -t 5m --seeded-users 1000 --password StressPass123!
locust -f stress_tests/locustfile.py --headless --host http://127.0.0.1:8000 -u 1000 -r 50 -t 15m --seeded-users 1000 --password StressPass123!
```

## Baseline Gates

`config.py` defines initial pass/fail gates:

- error rate <= `2.0%`
- p95 <= `1200ms`
- p99 <= `2500ms`
- non-http failures <= `0`

At test end, `locustfile.py` appends a row to `stress_tests/results/summary.csv`.

Summary columns:
- `phase`
- `users`
- `duration_seconds`
- `rps`
- `error_rate_pct`
- `p95_ms`
- `p99_ms`
- `gate_status`
- `notes` (UTC timestamp by default)

## Contention Scenarios Included

- repeated patches to the same transaction ID
- repeated puts to the same source
- repeated patches to the same category name
- repeated patches to the same expense name

## Suggested Run Order

1. seed/reset users
2. run `10 -> 50 -> 100 -> 250 -> 500 -> 1000`
3. review `results/summary.csv`
4. run Django internal integrity tests after each phase
