"""Bug report API endpoint."""

from django.conf import settings
from django.core.mail import send_mail
from drf_spectacular.utils import OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from loguru import logger

from finance.api_tools.serializers.base_serializers import BugReportSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Submit bug report email",
        description="Send a bug report to the configured admin email.",
        request=BugReportSerializer,
        responses={
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_500_INTERNAL_SERVER_ERROR: OpenApiTypes.OBJECT,
        },
        tags=["Users"],
    ),
)
class BugReportView(APIView):
    def post(self, request):
        serializer = BugReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient = getattr(settings, "BUG_REPORT_TO_EMAIL", "")
        if not recipient:
            logger.error("bug_report_config_missing recipient_email is not configured")
            return Response(
                {"message": "Bug report destination is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        subject = serializer.validated_data["subject"]
        message = serializer.validated_data["message"]
        user = request.user
        user_line = f"user={getattr(user, 'username', 'unknown')} email={getattr(user, 'email', 'unknown')}"
        full_message = f"{user_line}\n\n{message}"

        send_mail(
            subject=f"[Finance Manager Bug Report] {subject}",
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("bug_report_sent subject={} recipient={}", subject, recipient)
        return Response({"message": "Bug report sent."}, status=status.HTTP_202_ACCEPTED)
