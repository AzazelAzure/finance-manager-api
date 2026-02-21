from rest_framework import serializers

class TagSerializer(serializers.Serializer):
    name = serializers.CharField()

class SourceSerializer(serializers.Serializer):
    source = serializers.CharField()
    acc_type = serializers.ChoiceField(max_length=10)

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
    currency = CurrencySerializer(required=False)
    is_recurring = serializers.BooleanField(required=False)

class TransactionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=200
        )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    source = SourceSerializer()
    currency = CurrencySerializer()
    tags = TagSerializer(many=True)
    tx_type = serializers.CharField(max_length=10)
    bill = ExpenseSerializer(required=False)
    tx_id = serializers.CharField(max_length=200, required=False)
    entry_id = serializers.CharField(max_length=200, required=False)

class AssetSerializer(serializers.Serializer):
    source = SourceSerializer()
    currency = CurrencySerializer()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class AppProfileSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    user_id = serializers.UUIDField(required=False)
    spend_accounts = SourceSerializer(many=True, required=False)
    base_currency = CurrencySerializer(required=False)


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