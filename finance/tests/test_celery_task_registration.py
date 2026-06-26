from django.conf import settings
from django.test import SimpleTestCase

from finance_api.celery import app


class CeleryBeatTaskRegistrationTests(SimpleTestCase):
    """Guard against beat-scheduled tasks not being registered with the worker.

    Regression: ``finance/tasks/`` lacked an ``__init__`` that imported the task
    submodules, so ``autodiscover_tasks`` only picked up tasks imported elsewhere
    (``notify_operator`` via the support view). Beat would then dispatch
    ``rollup_daily_usage`` / the weekly digest to a worker that discarded them.
    """

    def test_all_beat_scheduled_tasks_are_registered(self):
        app.loader.import_default_modules()
        registered = set(app.tasks.keys())
        scheduled = {entry["task"] for entry in settings.CELERY_BEAT_SCHEDULE.values()}
        missing = scheduled - registered
        self.assertEqual(missing, set(), f"Unregistered beat tasks: {sorted(missing)}")

    def test_notify_operator_registered(self):
        app.loader.import_default_modules()
        self.assertIn("finance.tasks.notify.notify_operator", app.tasks)
