from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer


class ExpenseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField(required=False)
    currency = serializers.CharField(max_length=3, required=False)
    is_recurring = serializers.BooleanField(required=False)

class ExpensePostSerializer(ExpenseSerializer):
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)


class ExpensePutSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField(allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField()
    currency = serializers.CharField(max_length=3)
    is_recurring = serializers.BooleanField()


class ExpensePatchSerializer(ExpenseSerializer):
    pass

class ExpenseSetReturnSerializer(ExpenseSerializer):
    rejected = ExpenseSerializer(many=True, required=False)
    accepted = ExpenseSerializer(many=True, required=False)
    updated = ExpenseSerializer(many=True, required=False)
    deleted = ExpenseSerializer(many=True, required=False)
    snapshot = FinancialSnapshotSerializer(required=False)


class ExpenseGetReturnSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)