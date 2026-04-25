from decimal import Decimal

from rest_framework import status

from finance.tests.source_tests.source_base import SourceBase


class SourcePostTestCase(SourceBase):
    def test_post_single_valid_source_persists_and_normalizes(self):
        response = self.client.post(self.url, self.source_data, format="json")
        self.assert_source_post_response(response, self.source_normalized_data, code=status.HTTP_201_CREATED)

    def test_post_single_rejects_unknown_source(self):
        payload = self.source_data.copy()
        payload["source"] = "unknown"

        response = self.client.post(self.url, payload, format="json")
        self.assert_source_post_response(response, self.source_normalized_data, code=status.HTTP_400_BAD_REQUEST)

    def test_post_single_rejects_unknown_account_type(self):
        payload = self.source_data.copy()
        payload["acc_type"] = "UNKNOWN"

        response = self.client.post(self.url, payload, format="json")
        self.assert_source_post_response(response, self.source_normalized_data, code=status.HTTP_400_BAD_REQUEST)

    def test_post_single_rejects_invalid_amount_types(self):
        invalid_amounts = ["not-a-number", [], {}, (), None]
        for invalid in invalid_amounts:
            payload = self.source_data.copy()
            payload["amount"] = invalid
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=f"amount={invalid!r}")

    def test_post_single_rejects_invalid_amount_precision(self):
        payload = self.source_data.copy()
        # More than 2 decimal places should be rejected by DecimalField.
        payload["amount"] = "123.456"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_single_rejects_missing_required_fields(self):
        payload_missing_source = self.source_data.copy()
        payload_missing_source.pop("source", None)
        response = self.client.post(self.url, payload_missing_source, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload_missing_acc_type = self.source_data.copy()
        payload_missing_acc_type.pop("acc_type", None)
        response = self.client.post(self.url, payload_missing_acc_type, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_single_rejects_invalid_account_type(self):
        payload = self.source_data.copy()
        payload["acc_type"] = "NOT_A_TYPE"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_single_rejects_invalid_currency(self):
        payload = self.source_data.copy()
        payload["currency"] = "ZZZ"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_bulk_mixed_valid_and_invalid_sources(self):
        valid_payload = {
            "source": "BulkValid-1",
            "acc_type": "cash",
            "amount": Decimal("10.00"),
            "currency": self.currency_value,
        }
        invalid_payload = {
            "source": "unknown",
            "acc_type": "cash",
            "amount": Decimal("5.00"),
            "currency": self.currency_value,
        }

        expected_valid = self._normalize_source_payload(valid_payload.copy())
        payloads = [valid_payload, invalid_payload]

        response = self.client.post(self.url, payloads, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn("accepted", response.data)
        self.assertIn("rejected", response.data)
        self.assertEqual(len(response.data["accepted"]), 1)
        self.assertGreaterEqual(len(response.data["rejected"]), 1)

        self.assert_source_post_response(response, expected_valid, code=status.HTTP_201_CREATED, index=0)

        # Ensure only the accepted payload was persisted.
        from finance.models import PaymentSource

        self.assertTrue(
            PaymentSource.objects.for_user(self.profile.user_id)
            .get_by_source(source=expected_valid["source"])
            .exists()
        )
        rejected_sources = [row.get("source") for row in response.data["rejected"] if isinstance(row, dict)]
        self.assertIn("unknown", [str(src).lower() for src in rejected_sources])

