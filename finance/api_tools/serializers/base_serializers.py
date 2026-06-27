from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
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
    tos_version = serializers.CharField(max_length=20, required=True)
    tos_accepted_at = serializers.DateTimeField(required=False, write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_tos_version(self, value):
        allowed = {"1.0"}
        if value not in allowed:
            raise serializers.ValidationError("Unsupported Terms of Service version.")
        return value

    def validate(self, attrs):
        if not attrs.get("tos_accepted_at"):
            raise serializers.ValidationError(
                {"tos_accepted_at": "Terms of Service acceptance timestamp is required."}
            )
        return attrs

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        validate_password(value, user=user)
        return value


class BugReportSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=120)
    message = serializers.CharField(max_length=4000)
