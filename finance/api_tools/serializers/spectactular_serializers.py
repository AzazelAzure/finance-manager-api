from rest_framework import serializers
from finance.api_tools.serializers.tx_serializers import TransactionSerializer
from finance.api_tools.serializers.exp_serializers import ExpenseSerializer



class SpectacularTxSerializer(serializers.Serializer):
    transactions = TransactionSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class SpectacularExpenseSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)