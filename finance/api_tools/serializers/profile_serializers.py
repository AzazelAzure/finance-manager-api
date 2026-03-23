from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer
from .tx_serializers import TransactionAcceptedSerializer


class AppProfileUpdateSerializer(serializers.Serializer):
    message = serializers.CharField()
    snapshot = FinancialSnapshotSerializer()

class AppProfileGetSerializer(serializers.Serializer):
    spend_accounts = serializers.ListField(child=serializers.CharField(max_length=50))
    base_currency = serializers.CharField(max_length=3)
    timezone = serializers.CharField(max_length=30)
    start_of_week = serializers.IntegerField()

class SnapshotSerializer(serializers.Serializer):
    snapshot = FinancialSnapshotSerializer()
    transactions_for_month = TransactionAcceptedSerializer(many=True)
    total_expenses_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)