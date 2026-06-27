from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from finance.tasks.security_alerts import check_security_thresholds


class SecurityAlertTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(
        SECURITY_ALERT_THRESHOLDS={
            "auth_failure": 10,
            "invalid_endpoint": 20,
            "5xx_rate_pct": 5,
        },
        SECURITY_ALERT_DEDUP_TTL=7200,
    )
    @patch("finance.tasks.security_alerts.notify_operator.delay")
    @patch(
        "finance.tasks.security_alerts.redis_keys",
        side_effect=lambda pattern: (
            ["fm_security:2026-06-27-14:deadbeefcafebabe:auth_failure"]
            if "auth_failure" in pattern
            else []
        ),
    )
    @patch("finance.tasks.security_alerts.redis_get_int", return_value=11)
    @patch(
        "finance.tasks.security_alerts.datetime",
    )
    def test_auth_failure_threshold_fires_once(self, mock_datetime, _mock_get, _mock_keys, mock_delay):
        from datetime import datetime, timezone

        mock_datetime.now.return_value = datetime(2026, 6, 27, 14, 15, tzinfo=timezone.utc)
        check_security_thresholds.run()
        self.assertEqual(mock_delay.call_count, 1)
        self.assertEqual(mock_delay.call_args.kwargs["event_type"], "SECURITY_PROBE_DETECTED")

        check_security_thresholds.run()
        self.assertEqual(mock_delay.call_count, 1)

    @override_settings(
        SECURITY_ALERT_THRESHOLDS={
            "auth_failure": 10,
            "invalid_endpoint": 20,
            "5xx_rate_pct": 5,
        },
    )
    @patch("finance.tasks.security_alerts.notify_operator.delay")
    @patch(
        "finance.tasks.security_alerts.redis_keys",
        side_effect=lambda pattern: (
            [
                "fm_metrics:2026-06-27:/api/health/:GET:2xx:user",
                "fm_metrics:2026-06-27:/api/health/:GET:5xx:user",
            ]
            if pattern.startswith("fm_metrics:")
            else []
        ),
    )
    @patch(
        "finance.tasks.security_alerts.redis_get_int",
        side_effect=lambda key: 94 if ":2xx:" in key else 6,
    )
    @patch("finance.tasks.security_alerts.datetime")
    def test_5xx_rate_threshold_fires(self, mock_datetime, _mock_get, _mock_keys, mock_delay):
        from datetime import datetime, timezone

        mock_datetime.now.return_value = datetime(2026, 6, 27, 14, 15, tzinfo=timezone.utc)
        check_security_thresholds.run()
        self.assertEqual(mock_delay.call_count, 1)
        notes = mock_delay.call_args.kwargs["notes"]
        self.assertIn("5xx error rate", notes)

    @override_settings(
        SECURITY_ALERT_THRESHOLDS={
            "auth_failure": 10,
            "invalid_endpoint": 20,
            "5xx_rate_pct": 5,
        },
    )
    @patch("finance.tasks.security_alerts.notify_operator.delay")
    @patch(
        "finance.tasks.security_alerts.redis_keys",
        side_effect=lambda pattern: (
            [
                "fm_metrics:2026-06-27:/api/health/:GET:2xx:user",
                "fm_metrics:2026-06-27:/api/health/:GET:5xx:user",
            ]
            if pattern.startswith("fm_metrics:")
            else []
        ),
    )
    @patch(
        "finance.tasks.security_alerts.redis_get_int",
        side_effect=lambda key: 96 if ":2xx:" in key else 4,
    )
    @patch("finance.tasks.security_alerts.datetime")
    def test_5xx_rate_below_threshold_is_silent(self, mock_datetime, _mock_get, _mock_keys, mock_delay):
        from datetime import datetime, timezone

        mock_datetime.now.return_value = datetime(2026, 6, 27, 14, 15, tzinfo=timezone.utc)
        check_security_thresholds.run()
        mock_delay.assert_not_called()
