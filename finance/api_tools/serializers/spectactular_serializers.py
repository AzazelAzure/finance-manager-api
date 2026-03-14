from rest_framework import serializers
from base_serializers import TransactionSerializer, ExpenseSerializer


class SpectacularTxSerializer(serializers.Serializer):
    transactions = TransactionSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class SpectacularExpenseSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)