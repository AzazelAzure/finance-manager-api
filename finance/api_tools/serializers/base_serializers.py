from rest_framework import serializers

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

class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    user_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)




