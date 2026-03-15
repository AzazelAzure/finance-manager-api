from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer

class TransactionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=200
        )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    source = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=3)
    tags = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    tx_type = serializers.CharField(max_length=10)
    category = serializers.CharField(max_length=200, required=False)

class TransactionSetSerializer(TransactionSerializer):
    bill = serializers.CharField(max_length=200, required=False)

class TransactionAcceptedSerializer(TransactionSetSerializer):
    tx_id = serializers.CharField(max_length=20)
    created_on = serializers.DateField()

class TransactionSetReturnSerializer(serializers.Serializer):
    rejected = TransactionSetSerializer(many=True, required=False)
    accepted = TransactionAcceptedSerializer(many=True, required=False)
    updated = TransactionAcceptedSerializer(many=True, required=False)
    snapshot = FinancialSnapshotSerializer(required=False)

class TransactionGetSerializer(TransactionSerializer):
    tx_id = serializers.CharField(max_length=20)
    created_on = serializers.DateField()
    bill = serializers.CharField(max_length=200, required=False)
    snapshot = FinancialSnapshotSerializer(required=False)


class TransactionGetReturnSerializer(serializers.Serializer):
    transactions = TransactionGetSerializer(many=True)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_leaks = serializers.DecimalField(max_digits=10, decimal_places=2)