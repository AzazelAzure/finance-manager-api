from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer
from .tx_serializers import TransactionAcceptedSerializer


class AppProfileUpdateSerializer(serializers.Serializer):
    message = serializers.CharField()
    snapshot = FinancialSnapshotSerializer()

class AppProfileGetSerializer(serializers.Serializer):
    spend_accounts = serializers.ListField(child=serializers.CharField(max_length=50))
    base_currency = serializers.CharField(max_length=3)
    timezone = serializers.CharField(max_length=64)
    start_of_week = serializers.IntegerField()
    completed_tours = serializers.ListField(child=serializers.CharField(max_length=200), required=False, allow_null=True)
    feature_requests_enabled = serializers.BooleanField(read_only=True)

class SnapshotSerializer(serializers.Serializer):
    # user_get_totals can return snapshot=None before onboarding/first snapshot row exists
    snapshot = FinancialSnapshotSerializer(allow_null=True, required=False)
    transactions_for_month = TransactionAcceptedSerializer(many=True)
    flow_series = serializers.ListField(child=serializers.DictField(), required=False)
    expense_by_category = serializers.ListField(child=serializers.DictField(), required=False)
    source_balances = serializers.ListField(child=serializers.DictField(), required=False)
    daily_spend = serializers.ListField(child=serializers.DictField(), required=False)
    daily_income = serializers.ListField(child=serializers.DictField(), required=False)
    total_expenses_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_leaks_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)