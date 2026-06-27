import json
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from finance.models import DailyUsageSnapshot
from finance.tasks.analytics import rollup_daily, rollup_metrics_hourly, rollup_weekly
from finance.utils.observability_keys import parse_metric_key, parse_security_key


class ObservabilityKeyParsingTests(SimpleTestCase):
    def test_parse_metric_key(self):
        key = "fm_metrics:2026-06-27:/api/health/:GET:2xx:user"
        parts = parse_metric_key(key)
        self.assertIsNotNone(parts)
        assert parts is not None
        self.assertEqual(parts.endpoint, "/api/health/")
        self.assertEqual(parts.method, "GET")

    def test_parse_security_key(self):
        key = "fm_security:2026-06-27-14:abcd1234ef567890:auth_failure"
        parts = parse_security_key(key)
        self.assertIsNotNone(parts)
        assert parts is not None
        self.assertEqual(parts.ip_hash, "abcd1234ef567890")
        self.assertEqual(parts.event_type, "auth_failure")


class AnalyticsRollupTests(SimpleTestCase):
    @override_settings(ANALYTICS_LOG_DIR="/tmp/fm-analytics-test")
    @patch("finance.tasks.analytics.redis_delete")
    @patch("finance.tasks.analytics.redis_get_int", return_value=7)
    @patch(
        "finance.tasks.analytics.redis_keys",
        return_value=["fm_metrics:2026-06-27:/api/health/:GET:2xx:user"],
    )
    @patch("finance.tasks.analytics.datetime")
    def test_rollup_metrics_hourly_writes_and_consumes_keys(
        self, mock_datetime, _mock_keys, _mock_get, mock_delete
    ):
        from datetime import datetime, timezone

        mock_datetime.now.return_value = datetime(2026, 6, 27, 14, 5, tzinfo=timezone.utc)
        with patch("finance.tasks.analytics._analytics_dir") as mock_dir:
            tmp = self._tmpdir()
            mock_dir.return_value = tmp
            result = rollup_metrics_hourly.run()
            self.assertIn("rollup:", result)
            metrics_path = f"{tmp}/metrics_2026-06-27.jsonl"
            with open(metrics_path, encoding="utf-8") as handle:
                row = json.loads(handle.readline())
            self.assertEqual(row["count"], 7)
            self.assertEqual(row["endpoint"], "/api/health/")
            mock_delete.assert_called_once()

    @staticmethod
    def _tmpdir():
        import tempfile

        return tempfile.mkdtemp()

    @override_settings(ANALYTICS_LOG_DIR="/tmp/fm-analytics-test")
    @patch("finance.tasks.analytics.datetime")
    def test_rollup_metrics_hourly_is_idempotent_per_key(self, mock_datetime):
        from datetime import datetime, timezone

        mock_datetime.now.return_value = datetime(2026, 6, 27, 14, 5, tzinfo=timezone.utc)
        import tempfile

        tmp = tempfile.mkdtemp()
        with patch("finance.tasks.analytics._analytics_dir", return_value=tmp):
            with patch(
                "finance.tasks.analytics.redis_keys",
                return_value=["fm_metrics:2026-06-27:/api/health/:GET:2xx:user"],
            ):
                with patch("finance.tasks.analytics.redis_get_int", return_value=3):
                    with patch("finance.tasks.analytics.redis_delete") as mock_delete:
                        rollup_metrics_hourly.run()
                        mock_delete.assert_called_once()
            with patch("finance.tasks.analytics.redis_keys", return_value=[]):
                result = rollup_metrics_hourly.run()
                self.assertIn("noop:", result)


class AnalyticsDailyWeeklyTests(TestCase):
    def test_rollup_daily_includes_dau_mau(self):
        import tempfile
        from datetime import date, datetime, timezone

        yesterday = date(2026, 6, 26)
        DailyUsageSnapshot.objects.create(date=yesterday, dau_count=7, mau_count=23)

        tmp = tempfile.mkdtemp()
        metrics_path = f"{tmp}/metrics_{yesterday}.jsonl"
        with open(metrics_path, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "ts": "2026-06-26T14:00:00Z",
                        "endpoint": "/api/health/",
                        "method": "GET",
                        "response_class": "2xx",
                        "ua_class": "user",
                        "count": 5,
                    }
                )
                + "\n"
            )

        with patch("finance.tasks.analytics._analytics_dir", return_value=tmp):
            with patch("finance.tasks.analytics.datetime") as mock_datetime:
                mock_datetime.now.return_value = datetime(
                    2026, 6, 27, 0, 10, tzinfo=timezone.utc
                )
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                rollup_daily.run()

            daily_path = f"{tmp}/daily_{yesterday}.json"
            with open(daily_path, encoding="utf-8") as handle:
                summary = json.load(handle)
            self.assertEqual(summary["dau"], 7)
            self.assertEqual(summary["mau"], 23)
            self.assertEqual(summary["total_requests"], 5)

    def test_rollup_weekly_skips_when_file_exists(self):
        import tempfile
        from datetime import datetime, timezone

        tmp = tempfile.mkdtemp()
        fixed_today = datetime(2026, 6, 30, 0, 10, tzinfo=timezone.utc)
        week_str = fixed_today.strftime("%Y-W%W")
        week_path = f"{tmp}/weekly_{week_str}.json"
        with open(week_path, "w", encoding="utf-8") as handle:
            handle.write("{}")

        with patch("finance.tasks.analytics._analytics_dir", return_value=tmp):
            with patch("finance.tasks.analytics.datetime") as mock_datetime:
                mock_datetime.now.return_value = fixed_today
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                result = rollup_weekly.run()
            self.assertIn("skip:", result)
