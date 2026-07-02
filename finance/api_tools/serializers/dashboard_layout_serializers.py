from rest_framework import serializers


class DashboardLayoutItemSerializer(serializers.Serializer):
    widget_id = serializers.CharField()
    size = serializers.ChoiceField(choices=["full", "half"])
    visible = serializers.BooleanField()


class DashboardLayoutResponseSerializer(serializers.Serializer):
    device_class = serializers.ChoiceField(choices=["mobile", "desktop"])
    layout = DashboardLayoutItemSerializer(many=True)
    is_default = serializers.BooleanField()
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class DashboardLayoutUpsertSerializer(serializers.Serializer):
    device_class = serializers.ChoiceField(choices=["mobile", "desktop"])
    layout = DashboardLayoutItemSerializer(many=True)


class DashboardLayoutResetSerializer(serializers.Serializer):
    device_class = serializers.ChoiceField(choices=["mobile", "desktop"])
