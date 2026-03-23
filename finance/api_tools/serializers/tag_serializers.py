from rest_framework import serializers

class TagSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField(max_length=200))


class TagPatchPutSerializer(serializers.Serializer):
    tags = serializers.DictField(
        child=serializers.CharField(allow_null=True, allow_blank=True, required=False),
    )


class TagSetSerializer(TagSerializer):
    pass


class TagSetReturnSerializer(serializers.Serializer):
    accepted = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    rejected = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    updated = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    deleted = serializers.ListField(child=serializers.CharField(max_length=200), required=False)