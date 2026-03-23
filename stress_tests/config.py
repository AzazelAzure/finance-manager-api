"""Shared configuration for API stress testing with Locust."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


DEFAULT_HOST = os.getenv("STRESS_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_PASSWORD = os.getenv("STRESS_PASSWORD", "StressPass123!")
DEFAULT_USER_PREFIX = os.getenv("STRESS_USER_PREFIX", "stress_user")
DEFAULT_EMAIL_DOMAIN = os.getenv("STRESS_EMAIL_DOMAIN", "example.com")
DEFAULT_SPAWN_RATE_DIVISOR = int(os.getenv("STRESS_SPAWN_RATE_DIVISOR", "10"))
DEFAULT_RUN_TIME_SECONDS = int(os.getenv("STRESS_RUN_TIME_SECONDS", "300"))
DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_REQUEST_TIMEOUT = float(os.getenv("STRESS_REQUEST_TIMEOUT", "15"))


RUN_PROFILES: Dict[str, Dict[str, int]] = {
    "10": {"users": 10, "spawn_rate": 2, "run_time_seconds": 180},
    "50": {"users": 50, "spawn_rate": 5, "run_time_seconds": 240},
    "100": {"users": 100, "spawn_rate": 10, "run_time_seconds": 300},
    "250": {"users": 250, "spawn_rate": 20, "run_time_seconds": 420},
    "500": {"users": 500, "spawn_rate": 35, "run_time_seconds": 600},
    "1000": {"users": 1000, "spawn_rate": 50, "run_time_seconds": 900},
}


PASS_FAIL_GATES = {
    "error_rate_max_pct": 2.0,
    "p95_ms_max": 1200,
    "p99_ms_max": 2500,
    "non_http_failures_max": 0,
}


SUMMARY_HEADERS = [
    "phase",
    "users",
    "duration_seconds",
    "rps",
    "error_rate_pct",
    "p95_ms",
    "p99_ms",
    "gate_status",
    "notes",
]


@dataclass(frozen=True)
class SeedDefaults:
    """Deterministic seed constants consumed by seed_data and user flows."""

    sources_per_user: int = 4
    categories_per_user: int = 4
    tags_per_user: int = 4
    expenses_per_user: int = 2


SEED_DEFAULTS = SeedDefaults()
