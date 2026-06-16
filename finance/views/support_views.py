from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view
from finance.api_tools.serializers.support_serializers import SupportTicketSerializer

import os
from django.conf import settings
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

            if ticket.report_type == "BUG":
                from finance.utils.incident_extractor import extract_incident_logs
                user_id = str(request.user.appprofile.user_id)
                possible_log_paths = [
                    os.path.join(settings.BASE_DIR, "logs", "diagnostic", f"{user_id}.log"),
                    os.path.join(settings.BASE_DIR, "finance", "logs", "diagnostic", f"{user_id}.log"),
                ]
                log_path = None
                for path in possible_log_paths:
                    if os.path.exists(path):
                        log_path = path
                        break

                extracted_logs = []
                if log_path:
                    extracted_logs = extract_incident_logs(log_path, ticket.created_at)

                # b. Format and write incident report
                incident_filename = f"incident_{ticket.id}.log"
                report_content = (
                    f"Ticket ID: {ticket.id}\n"
                    f"User ID: {ticket.uid}\n"
                    f"Nature: {ticket.nature}\n"
                    f"Severity: {ticket.severity}\n"
                    f"Comment: {ticket.comment}\n"
                    f"Created At: {ticket.created_at}\n\n"
                    f"=== EXTRACTED 10-MINUTE LOG WINDOW ===\n"
                )
                if extracted_logs:
                    report_content += "".join(extracted_logs)
                else:
                    report_content += "[No logs found in the preceding 10-minute window]\n"

                locations = [
                    os.path.join(settings.BASE_DIR, "logs", "incidents"),
                    os.path.join(settings.BASE_DIR, "finance", "logs", "incidents")
                ]
                for loc in locations:
                    try:
                        os.makedirs(loc, exist_ok=True)
                        with open(os.path.join(loc, incident_filename), 'w', encoding='utf-8') as f:
                            f.write(report_content)
                    except Exception:
                        pass

                # c. Save relative path in diagnostic_log_key and save ticket
                ticket.diagnostic_log_key = f"logs/incidents/incident_{ticket.id}.log"
                ticket.save()

                # d. Send immediate email containing bug ticket details
                recipient = getattr(settings, "BUG_REPORT_TO_EMAIL", "")
                if recipient:
                    from django.core.mail import send_mail
                    user_str = f"User UUID: {ticket.uid}"
                    if request.user:
                        user_str += f" (Username: {request.user.username}, Email: {request.user.email})"
                    subject = f"[Support Bug Ticket] {ticket.nature}"
                    email_body = (
                        f"Ticket ID: {ticket.id}\n"
                        f"User: {user_str}\n"
                        f"Nature: {ticket.nature}\n"
                        f"Severity: {ticket.severity}\n"
                        f"Comment: {ticket.comment}\n"
                        f"Created At: {ticket.created_at}\n"
                        f"Diagnostic Log Key: {ticket.diagnostic_log_key}\n"
                    )
                    send_mail(
                        subject=subject,
                        message=email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient],
                        fail_silently=False,
                    )
                    ticket.emailed = True
                    ticket.save()

            response_serializer = SupportTicketSerializer(ticket)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
