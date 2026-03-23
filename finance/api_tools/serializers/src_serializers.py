from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer

class SourceSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=50, required=False)
    acc_type = serializers.CharField(max_length=10, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    currency = serializers.CharField(max_length=3, required=False)

class SourcePostSerializer(SourceSerializer):
    source = serializers.CharField(max_length=50)
    acc_type = serializers.CharField(max_length=10)


class SourcePatchSerializer(SourceSerializer):
    pass


class SourcePutSerializer(SourceSerializer):
    source = serializers.CharField(max_length=50)
    acc_type = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)


class SourceSetReturnSerializer(SourceSerializer):
    rejected = SourceSerializer(many=True, required=False)
    accepted = SourceSerializer(many=True, required=False)
    updated = SourceSerializer(required=False)
    deleted = SourceSerializer(required=False)
    snapshot = FinancialSnapshotSerializer(required=False)

