from rest_framework import serializers
from django.conf import settings
from finance.models import SupportTicket

class SupportTicketSerializer(serializers.ModelSerializer):
    nature = serializers.CharField(max_length=255)
    comment = serializers.CharField(min_length=10)

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "report_type",
            "severity",
            "nature",
            "comment",
            "diagnostic_log_key",
            "created_at",
            "emailed",
        ]
        read_only_fields = ["id", "created_at", "emailed"]

    def validate(self, attrs):
        report_type = attrs.get("report_type")
        if report_type == SupportTicket.ReportType.FEATURE:
            if not getattr(settings, "BETA_FEATURE_REQUESTS_ENABLED", False):
                raise serializers.ValidationError(
                    {"report_type": "Feature requests are currently disabled."}
                )
        return attrs
