from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view
from finance.api_tools.serializers.support_serializers import SupportTicketSerializer

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
            serializer.save(uid=str(request.user.appprofile.user_id))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
