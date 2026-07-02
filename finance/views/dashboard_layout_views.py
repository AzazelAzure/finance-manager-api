from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.api_tools.serializers.dashboard_layout_serializers import (
    DashboardLayoutResetSerializer,
    DashboardLayoutResponseSerializer,
    DashboardLayoutUpsertSerializer,
)
from finance.services import dashboard_layout_services as layout_svc


def _uid(request) -> str:
    return str(request.user.appprofile.user_id)


def _validation_response(exc: ValidationError) -> Response:
    detail = exc.detail
    if isinstance(detail, list):
        message = detail[0] if detail else "Validation error"
    elif isinstance(detail, dict):
        first_key = next(iter(detail))
        value = detail[first_key]
        message = value[0] if isinstance(value, list) and value else str(value)
    else:
        message = str(detail)
    return Response({"detail": str(message)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_dashboard_layout_retrieve",
        summary="Retrieve dashboard layout",
        description=(
            "Return the saved dashboard layout for the requested device class, "
            "or the device-appropriate default when the user has not customized."
        ),
        parameters=[
            OpenApiParameter(
                name="device_class",
                type=str,
                enum=["mobile", "desktop"],
                required=True,
            ),
        ],
        responses={status.HTTP_200_OK: DashboardLayoutResponseSerializer},
        tags=["Dashboard Layout"],
    ),
    put=extend_schema(
        operation_id="finance_dashboard_layout_update",
        summary="Replace dashboard layout",
        request=DashboardLayoutUpsertSerializer,
        responses={
            status.HTTP_200_OK: DashboardLayoutResponseSerializer,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=["Dashboard Layout"],
    ),
    patch=extend_schema(
        operation_id="finance_dashboard_layout_partial_update",
        summary="Upsert dashboard layout",
        request=DashboardLayoutUpsertSerializer,
        responses={
            status.HTTP_200_OK: DashboardLayoutResponseSerializer,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=["Dashboard Layout"],
    ),
)
class DashboardLayoutView(APIView):
    """CRUD for per-user, per-device-class dashboard widget layouts (F-006 T01)."""

    def get(self, request):
        device_class = request.query_params.get("device_class")
        if not device_class:
            return Response(
                {"detail": "device_class query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = layout_svc.get_dashboard_layout(_uid(request), device_class)
        except ValidationError as exc:
            return _validation_response(exc)
        serializer = DashboardLayoutResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        return self._upsert(request)

    def patch(self, request):
        return self._upsert(request)

    def _upsert(self, request):
        try:
            payload = layout_svc.upsert_dashboard_layout(_uid(request), request.data)
        except ValidationError as exc:
            return _validation_response(exc)
        serializer = DashboardLayoutResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        operation_id="finance_dashboard_layout_reset",
        summary="Reset dashboard layout to default",
        description="Restore the server default layout for one device class variant only.",
        request=DashboardLayoutResetSerializer,
        responses={
            status.HTTP_200_OK: DashboardLayoutResponseSerializer,
            status.HTTP_400_BAD_REQUEST: None,
        },
        tags=["Dashboard Layout"],
    ),
)
class DashboardLayoutResetView(APIView):
    def post(self, request):
        device_class = request.data.get("device_class")
        if not device_class:
            return Response(
                {"detail": "device_class is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = layout_svc.reset_dashboard_layout(_uid(request), device_class)
        except ValidationError as exc:
            return _validation_response(exc)
        serializer = DashboardLayoutResponseSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)
