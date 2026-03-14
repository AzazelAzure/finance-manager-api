from rest_framework import serializers

class TagSerializer(serializers.Serializer):
    tags = serializers.ListField(child=serializers.CharField(max_length=200), required=False)

class TagSetSerializer(TagSerializer):
    tags = TagSerializer(many=True)
    update = TagSerializer(many=True, required=False)
    to_delete = TagSerializer(many=True, required=False)
                              
class TagSetReturnSerializer(TagSerializer):
    accepted = TagSerializer(many=True, required=False)
    rejected = TagSerializer(many=True, required=False)
    updated = TagSerializer(many=True, required=False)
    deleted = TagSerializer(many=True, required=False)