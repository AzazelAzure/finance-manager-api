from rest_framework import serializers

class TagSerializer(serializers.Serializer):
    name = serializers.CharField()

class SourceSerializer(serializers.Serializer):
    source = serializers.CharField()
    acc_type = serializers.CharField(max_length=10)

class CurrencySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=3)
    name = serializers.CharField(max_length=50)
    symbol = serializers.CharField(max_length=10, required=False)


class ExpenseSerializer(serializers.Serializer):
    name = serializers.CharField()
    estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField(required=False)
    currency = serializers.CharField(max_length=3)
    start = serializers.DateField(required=False, allow_null=True)
    end = serializers.DateField(required=False, allow_null=True)
    recurring = serializers.BooleanField(required=False)
    is_recurring = serializers.BooleanField(required=False)

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
    tags = serializers.ListField(child=serializers.CharField(max_length=200))
    tx_type = serializers.CharField(max_length=10)
    bill = serializers.CharField(max_length=200, required=False)
    tx_id = serializers.CharField(max_length=200, required=False)
    entry_id = serializers.CharField(max_length=200, required=False)

class TransactionGetSerializer(serializers.Serializer):
    transactions = TransactionSerializer(many=True)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_leaks = serializers.DecimalField(max_digits=10, decimal_places=2)

class AssetSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=3)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class AppProfileSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    user_id = serializers.UUIDField(required=False)
    spend_accounts = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    base_currency = serializers.CharField(max_length=3, required=False)



class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    user_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class FinancialSnapshotSerializer(serializers.Serializer):
    safe_to_spend = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_assets = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_checking = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_investment = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cash = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_ewallet = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_monthly_spending = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_remaining_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_leaks = serializers.DecimalField(max_digits=10, decimal_places=2)

class SnapshotSerializer(serializers.Serializer):
    snapshot = FinancialSnapshotSerializer()
    transactions_for_month = TransactionSerializer(many=True)
    total_expenses_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in_for_month = serializers.DecimalField(max_digits=10, decimal_places=2)

class SpectacularTxSerializer(serializers.Serializer):
    transactions = TransactionSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class SpectacularExpenseSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)