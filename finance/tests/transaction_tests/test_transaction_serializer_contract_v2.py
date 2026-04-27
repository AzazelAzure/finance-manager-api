from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from finance.api_tools.serializers.tx_serializers import TransactionSetSerializer


class TransactionSerializerContractV2Tests(SimpleTestCase):
    def test_transaction_set_serializer_accepts_decimal_and_tags_payload(self):
        serializer = TransactionSetSerializer(
            data={
                "date": str(date.today()),
                "description": "Contract check",
                "amount": "123.45",
                "source": "cash-wallet",
                "currency": "USD",
                "tags": ["daily", "needs"],
                "tx_type": "EXPENSE",
                "category": "Food",
                "bill": "",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["amount"], Decimal("123.45"))
        self.assertEqual(serializer.validated_data["tags"], ["daily", "needs"])

    def test_transaction_set_serializer_allows_optional_category_and_null_bill(self):
        serializer = TransactionSetSerializer(
            data={
                "date": str(date.today()),
                "description": "",
                "amount": "50.00",
                "source": "cash-wallet",
                "currency": "USD",
                "tags": [],
                "tx_type": "INCOME",
                "bill": None,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("category", serializer.validated_data)
        self.assertIsNone(serializer.validated_data["bill"])

