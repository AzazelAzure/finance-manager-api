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
    bill = serializers.CharField(max_length=200, required=False)

class AssetSerializer(serializers.Serializer):
    source = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

class SourceSerializer(serializers.Serializer):
    source = serializers.CharField()
    acc_type = serializers.CharField(max_length=10)

class ExpenseSerializer(serializers.Serializer):
    name = serializers.CharField()
    estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField(required=False)
    expense_id = serializers.CharField(max_length=200, required=False)
    status = serializers.CharField(max_length=10, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    is_recurring = serializers.BooleanField(required=False)