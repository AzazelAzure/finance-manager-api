"""Pytest configuration shared across the test suite.

The transaction test base (and several factories) draw random currencies,
payment sources, and amounts without a fixed seed. That made the suite
non-deterministic: currency-conversion-sensitive assertions (e.g. calendar
month aggregates) passed or failed depending on which currency was picked,
which surfaced as flaky CI. Seeding every RNG source before each test makes
runs reproducible.
"""
import os
import random

import factory.random
import pytest
from faker import Faker

# Default seed; override with FM_TEST_SEED to reproduce a specific run.
TEST_RANDOM_SEED = int(os.getenv("FM_TEST_SEED", "20260628"))


@pytest.fixture(autouse=True)
def _seed_test_randomness():
    random.seed(TEST_RANDOM_SEED)
    factory.random.reseed_random(TEST_RANDOM_SEED)
    Faker.seed(TEST_RANDOM_SEED)
