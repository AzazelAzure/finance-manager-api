from datetime import datetime

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.api_tools.serializers.balance_serializers import BalanceHistoryResponseSerializer
from finance.logic.balance_snapshots import get_balance_history


class BalanceHistoryView(APIView):
    """Read day-end balance series for dashboard trend charts (F-001)."""

    @extend_schema(
        operation_id="finance_balance_history_list",
        summary="Balance history series",
        description="Day-end closing balances per payment source, converted to the user's base currency.",
        parameters=[
            OpenApiParameter(name="source", type=str, required=False),
            OpenApiParameter(
                name="range",
                type=str,
                enum=["7d", "30d", "90d", "all"],
                required=False,
            ),
            OpenApiParameter(name="start_date", type=str, required=False),
            OpenApiParameter(name="end_date", type=str, required=False),
        ],
        responses={status.HTTP_200_OK: BalanceHistoryResponseSerializer},
        tags=["Balance History"],
    )
    def get(self, request):
        profile = request.user.appprofile
        uid = str(profile.user_id)
        source = request.query_params.get("source")
        range_preset = request.query_params.get("range")
        start_raw = request.query_params.get("start_date")
        end_raw = request.query_params.get("end_date")
        start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else None
        end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
        payload = get_balance_history(
            uid,
            profile,
            source=source,
            range_preset=range_preset,
            start_date=start_date,
            end_date=end_date,
        )
        serializer = BalanceHistoryResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
