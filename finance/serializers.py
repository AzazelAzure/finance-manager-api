from rest_framework import serializers

class TransactionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=200
        )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    category = serializers.CharField()
    source = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    tags = serializers.ListField(required=False)
    tx_type = serializers.CharField(max_length=10)
    is_income = serializers.BooleanField(required=False)
