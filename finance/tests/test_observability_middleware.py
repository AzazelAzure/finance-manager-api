from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from finance.middleware.observability import ObservabilityMiddleware


class ObservabilityMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    @patch("finance.middleware.observability.incr_with_expire")
    def test_records_metric_counter(self, mock_incr):
        request = self.factory.get(
            "/api/health/",
            HTTP_USER_AGENT="Mozilla/5.0",
            REMOTE_ADDR="203.0.113.1",
        )
        middleware = ObservabilityMiddleware(lambda req: HttpResponse("ok", status=200))
        middleware(request)

        metric_calls = [call.args[0] for call in mock_incr.call_args_list if call.args[0].startswith("fm_metrics:")]
        self.assertEqual(len(metric_calls), 1)
        self.assertIn("/api/health/", metric_calls[0])
        self.assertIn(":GET:2xx:user", metric_calls[0])
        self.assertNotIn("203.0.113.1", metric_calls[0])
        self.assertNotIn("Mozilla", metric_calls[0])

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    @patch("finance.middleware.observability.incr_with_expire")
    def test_unmatched_path_buckets_metric_key(self, mock_incr):
        # Unauthenticated 404 spray must not create unbounded fm_metrics:* keys.
        request = self.factory.get(
            "/totally/made/up/4f3c2b1a/",
            HTTP_USER_AGENT="curl/8.0",
            REMOTE_ADDR="203.0.113.9",
        )
        middleware = ObservabilityMiddleware(lambda req: HttpResponse("missing", status=404))
        middleware(request)

        metric_calls = [
            call.args[0] for call in mock_incr.call_args_list if call.args[0].startswith("fm_metrics:")
        ]
        self.assertEqual(len(metric_calls), 1)
        self.assertIn("{unmatched}", metric_calls[0])
        self.assertNotIn("/totally/made/up/", metric_calls[0])

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    @patch("finance.middleware.observability.incr_with_expire")
    def test_records_invalid_endpoint_security_counter(self, mock_incr):
        request = self.factory.get(
            "/api/does-not-exist/",
            HTTP_USER_AGENT="curl/8.0",
            REMOTE_ADDR="203.0.113.2",
        )
        middleware = ObservabilityMiddleware(lambda req: HttpResponse("missing", status=404))
        middleware(request)

        security_calls = [
            call.args[0] for call in mock_incr.call_args_list if call.args[0].startswith("fm_security:")
        ]
        self.assertTrue(any(key.endswith(":invalid_endpoint") for key in security_calls))
        self.assertFalse(any("203.0.113.2" in key for key in security_calls))

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    @patch("finance.middleware.observability.incr_with_expire")
    def test_records_auth_failure_security_counter(self, mock_incr):
        request = self.factory.get(
            "/finance/transactions/",
            HTTP_USER_AGENT="Mozilla/5.0",
            REMOTE_ADDR="203.0.113.3",
        )
        middleware = ObservabilityMiddleware(lambda req: HttpResponse("denied", status=401))
        middleware(request)

        security_calls = [
            call.args[0] for call in mock_incr.call_args_list if call.args[0].startswith("fm_security:")
        ]
        self.assertTrue(any(key.endswith(":auth_failure") for key in security_calls))

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    @patch("finance.middleware.observability.incr_with_expire", side_effect=RuntimeError("redis down"))
    @patch("finance.middleware.observability.logger")
    def test_errors_do_not_break_response(self, mock_logger, _mock_incr):
        request = self.factory.get("/api/health/")
        middleware = ObservabilityMiddleware(lambda req: HttpResponse("ok", status=200))
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        mock_logger.error.assert_called_once()
