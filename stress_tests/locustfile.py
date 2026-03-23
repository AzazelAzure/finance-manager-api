"""Locust entrypoint for finance manager stress test scenarios."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from locust import events

from stress_tests.config import (
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_RESULTS_DIR,
    PASS_FAIL_GATES,
    RUN_PROFILES,
    SUMMARY_HEADERS,
)
from stress_tests.user_flows import FinanceStressUser


FinanceStressUser.host = DEFAULT_HOST


def _profile_for_users(user_count: int) -> str:
    for key, values in RUN_PROFILES.items():
        if values["users"] == user_count:
            return key
    return "custom"


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument(
        "--password",
        type=str,
        env_var="STRESS_PASSWORD",
        default=DEFAULT_PASSWORD,
        help="Password for seeded stress users",
    )
    parser.add_argument(
        "--username-template",
        type=str,
        env_var="STRESS_USERNAME_TEMPLATE",
        default="stress_user_{user_id}",
        help="Username template used by Locust users",
    )
    parser.add_argument(
        "--seeded-users",
        type=int,
        env_var="STRESS_SEEDED_USERS",
        default=1000,
        help="How many users were created by stress_tests/seed_data.py",
    )


def _safe_percentile(stats_entry, percentile: float) -> int:
    if stats_entry is None or stats_entry.num_requests == 0:
        return 0
    return int(stats_entry.get_response_time_percentile(percentile))


@events.quitting.add_listener
def _(environment, **kwargs):
    stats = environment.stats.total
    fail_ratio_pct = round((stats.fail_ratio or 0.0) * 100, 2)
    p95 = _safe_percentile(stats, 0.95)
    p99 = _safe_percentile(stats, 0.99)
    users = environment.runner.target_user_count if environment.runner else 0
    duration = int(environment.stats.last_request_timestamp - environment.stats.start_time) if environment.stats.start_time else 0
    gate_pass = (
        fail_ratio_pct <= PASS_FAIL_GATES["error_rate_max_pct"]
        and p95 <= PASS_FAIL_GATES["p95_ms_max"]
        and p99 <= PASS_FAIL_GATES["p99_ms_max"]
    )
    gate_status = "PASS" if gate_pass else "FAIL"
    phase = _profile_for_users(users)

    DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = Path(DEFAULT_RESULTS_DIR) / "summary.csv"
    write_header = not summary_file.exists()
    with summary_file.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(SUMMARY_HEADERS)
        writer.writerow(
            [
                phase,
                users,
                duration,
                round(stats.total_rps or 0.0, 2),
                fail_ratio_pct,
                p95,
                p99,
                gate_status,
                datetime.now(tz=UTC).isoformat(),
            ]
        )
