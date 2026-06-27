from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from finance.models import AppProfile, DailyUsageSnapshot, OperatorAlertState
from finance.tasks.usage_rollup import rollup_daily_usage


class UsageRollupTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="rollup_user",
            email="rollup@example.com",
            password="password123",
        )
        yesterday = timezone.now().date() - timedelta(days=1)
        self.user.last_login = timezone.make_aware(
            datetime.combine(yesterday, datetime.min.time().replace(hour=12))
        )
        self.user.save(update_fields=["last_login"])
        self.profile = AppProfile.objects.get(username=self.user)

    @override_settings(DAU_ALERT_THRESHOLDS="1,50,100")
    def test_rollup_is_idempotent_and_alerts_once(self):
        with patch("finance.tasks.usage_rollup.notify_operator.delay") as mock_notify:
            rollup_daily_usage()
            rollup_daily_usage()
            snapshot = DailyUsageSnapshot.objects.get()
            self.assertEqual(snapshot.dau_count, 1)
            self.assertEqual(DailyUsageSnapshot.objects.count(), 1)
            self.assertEqual(mock_notify.call_count, 1)
            self.assertTrue(
                OperatorAlertState.objects.filter(alert_key="dau_threshold_1").exists()
            )
