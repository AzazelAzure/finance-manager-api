from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.models import PaymentSource
from finance.tests.basetest import BaseTestCase


class SourceBase(BaseTestCase):
    """
    Shared scaffolding for payment source endpoint tests.

    Mirrors transaction test patterns:
    - canonical valid request payload
    - normalized expected payload (case/decimal formatting)
    - a single assertion helper that checks response + DB persistence
    """

    def setUp(self):
        super().setUp()
        self.url = reverse("sources")

        # Use explicit non-conflicting values (tests run with fresh DB per class).
        self.source_value = "TestSource-POST"
        self.acc_type_value = "cash"
        self.amount_value = Decimal("123.45")
        self.currency_value = self.profile.base_currency

        self.source_data = {
            "source": self.source_value,
            "acc_type": self.acc_type_value,
            "amount": self.amount_value,
            "currency": self.currency_value,
        }
        self.source_normalized_data = self._normalize_source_payload(self.source_data.copy())

    @staticmethod
    def _normalize_source_payload(data: dict) -> dict:
        # Updater/source validators normalize:
        # - source -> lower-case
        # - acc_type -> upper-case
        # - currency -> upper-case (via validation_core)
        # - amount -> Decimal with 2dp
        data["source"] = str(data["source"]).lower()
        data["acc_type"] = str(data["acc_type"]).upper()
        data["currency"] = str(data["currency"]).upper()
        data["amount"] = Decimal(str(data["amount"])).quantize(Decimal("0.01"))
        return data

    def assert_source_post_response(self, response, expected: dict, *, code: int = 201, index: int = 0):
        """
        Assertions for POST /finance/sources/.

        Expected response shape after service/view alignment:
        - On success: {'accepted': [ ... ], 'rejected': [ ... ], 'snapshot': {...}}
        - On validation error: HTTP 400 with DRF error body.
        """
        if code == status.HTTP_201_CREATED:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        elif code == status.HTTP_400_BAD_REQUEST:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            return
        else:
            self.assertEqual(response.status_code, code)
            return

        self.assertIn("accepted", response.data)
        accepted_rows = response.data["accepted"]
        self.assertIsInstance(accepted_rows, list)
        self.assertGreaterEqual(len(accepted_rows), 1)
        row = accepted_rows[index]

        for key, value in expected.items():
            if key == "uid":
                continue
            self.assertIn(key, row)
            if key == "amount":
                self.assertEqual(
                    Decimal(str(row[key])).quantize(Decimal("0.01")),
                    Decimal(str(value)).quantize(Decimal("0.01")),
                )
            else:
                self.assertEqual(row[key], value)

        # DB persistence check (sources are unique per user by (source, uid)).
        db_obj = (
            PaymentSource.objects.for_user(self.profile.user_id)
            .get_by_source(source=expected["source"])
            .first()
        )
        self.assertIsNotNone(db_obj)
        self.assertEqual(str(db_obj.source), expected["source"])
        self.assertEqual(db_obj.acc_type, expected["acc_type"])
        self.assertEqual(db_obj.currency, expected["currency"])
        self.assertEqual(
            Decimal(str(db_obj.amount)).quantize(Decimal("0.01")),
            Decimal(str(expected["amount"])).quantize(Decimal("0.01")),
        )

    def seed_source(self, source_name="seed-source", acc_type="cash", amount="25.00", currency=None):
        payload = {
            "source": source_name,
            "acc_type": acc_type,
            "amount": Decimal(str(amount)),
            "currency": currency or self.currency_value,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return self._normalize_source_payload(payload.copy())

    def assert_source_row(self, source_name: str, expected: dict):
        db_obj = PaymentSource.objects.for_user(self.profile.user_id).get_by_source(source_name).first()
        self.assertIsNotNone(db_obj)
        for key, value in expected.items():
            if key == "amount":
                self.assertEqual(
                    Decimal(str(db_obj.amount)).quantize(Decimal("0.01")),
                    Decimal(str(value)).quantize(Decimal("0.01")),
                )
            else:
                self.assertEqual(getattr(db_obj, key), value)

