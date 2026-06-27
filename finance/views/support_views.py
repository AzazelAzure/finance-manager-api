from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view
from finance.api_tools.serializers.support_serializers import SupportTicketSerializer
from finance.services.support_incident import (
    bug_severity_label,
    diagnostic_log_candidates,
    dump_bug_incident,
)
from finance.tasks.notify import notify_operator

from finance.models import SupportTicket

class SupportTicketThrottle(UserRateThrottle):
    rate = '20/minute'

@extend_schema_view(
    post=extend_schema(
        operation_id="support_ticket_create",
        summary="Create support ticket",
        description="Submit a bug report or feature request ticket.",
        request=SupportTicketSerializer,
        responses={
            status.HTTP_201_CREATED: SupportTicketSerializer,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=["Support Tickets"]
    )
)
class SupportTicketView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SupportTicketThrottle]
    serializer_class = SupportTicketSerializer

    def post(self, request):
        serializer = SupportTicketSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save(uid=str(request.user.appprofile.user_id))

            user_id = str(request.user.appprofile.user_id)
            diagnostic_paths = [f"logs/diagnostic/{user_id}.log"]

            if ticket.report_type == "BUG":
                ticket.diagnostic_log_key = dump_bug_incident(ticket, user_id)
                ticket.save(update_fields=["diagnostic_log_key"])
                if ticket.diagnostic_log_key:
                    diagnostic_paths.append(ticket.diagnostic_log_key)

                notify_operator.delay(
                    event_type="BUG_REPORT",
                    severity=bug_severity_label(ticket.severity),
                    user_ref=ticket.uid,
                    file_paths=diagnostic_paths,
                    notes=ticket.nature,
                )
                ticket.emailed = True
                ticket.save(update_fields=["emailed"])
            elif ticket.report_type == "FEATURE":
                notify_operator.delay(
                    event_type="FEATURE_REQUEST",
                    severity="info",
                    user_ref=ticket.uid,
                    file_paths=diagnostic_paths,
                    notes=ticket.nature,
                )
                ticket.emailed = True
                ticket.save(update_fields=["emailed"])

            response_serializer = SupportTicketSerializer(ticket)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
