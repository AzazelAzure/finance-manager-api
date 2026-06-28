from rest_framework import serializers


class BalanceHistoryPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    source = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()


class BalanceHistoryResponseSerializer(serializers.Serializer):
    series = BalanceHistoryPointSerializer(many=True)
    base_currency = serializers.CharField()
