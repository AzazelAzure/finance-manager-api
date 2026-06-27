from django.test import SimpleTestCase, override_settings

from finance.utils.observability_helpers import (
    classify_ua,
    hash_ip,
    normalize_endpoint,
    response_class_for_status,
)


class ObservabilityHelpersTests(SimpleTestCase):
    @override_settings(LOG_IP_HASH_SALT="test-salt")
    def test_normalize_endpoint_strips_ids(self):
        self.assertEqual(
            normalize_endpoint("/finance/transactions/42/"),
            "/finance/transactions/{id}/",
        )
        self.assertEqual(
            normalize_endpoint(
                "/finance/transactions/00000000-0000-0000-0000-000000000001/"
            ),
            "/finance/transactions/{uuid}/",
        )

    @override_settings(LOG_IP_HASH_SALT="test-salt")
    def test_hash_ip_is_salted_and_truncated(self):
        first = hash_ip("203.0.113.1")
        second = hash_ip("203.0.113.1")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        with override_settings(LOG_IP_HASH_SALT="other-salt"):
            self.assertNotEqual(first, hash_ip("203.0.113.1"))

    def test_classify_ua(self):
        self.assertEqual(classify_ua("Mozilla/5.0 Chrome/120"), "user")
        self.assertEqual(classify_ua("Googlebot/2.1"), "crawler")
        self.assertEqual(classify_ua("curl/8.0"), "bot")
        self.assertEqual(classify_ua(""), "unknown")

    def test_response_class_for_status(self):
        self.assertEqual(response_class_for_status(200), "2xx")
        self.assertEqual(response_class_for_status(404), "4xx")
        self.assertEqual(response_class_for_status(503), "5xx")
