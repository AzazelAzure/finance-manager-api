from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from finance.api_tools.serializers.tx_serializers import TransactionSetSerializer


class TransactionSerializerContractTests(SimpleTestCase):
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

