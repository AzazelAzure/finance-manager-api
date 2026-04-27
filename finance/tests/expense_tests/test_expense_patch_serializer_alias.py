from django.test import SimpleTestCase

from finance.api_tools.serializers.exp_serializers import ExpensePatchSerializer


class ExpensePatchSerializerAliasTestCase(SimpleTestCase):
    def test_paid_alias_maps_to_paid_flag(self):
        serializer = ExpensePatchSerializer(data={"paid": True})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data["paid_flag"])
        self.assertNotIn("paid", serializer.validated_data)

