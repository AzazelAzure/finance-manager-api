from rest_framework import serializers

class CategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)

class CategorySetReturnSerializer(serializers.Serializer):
    accepted = CategorySerializer(many=True, required=False)
    rejected = CategorySerializer(many=True, required=False)
    updated = CategorySerializer(required=False)
    deleted = CategorySerializer(required=False)

class CategoryGetReturnSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True, required=False)
    category = CategorySerializer(required=False)