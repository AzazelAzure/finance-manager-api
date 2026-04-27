from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view

# Service Imports
import finance.services.user_services as user_svc

# Serializer Imports
from finance.api_tools.serializers.profile_serializers import(
    AppProfileGetSerializer,
    AppProfileUpdateSerializer,
    SnapshotSerializer
)



@extend_schema_view(
    get=extend_schema(
        operation_id="finance_profile_retrieve",
        summary="Retrieve app profile",
        description="Retrieve profile settings. Detailed snapshot totals are available on the snapshot route.",
        responses={status.HTTP_200_OK: AppProfileGetSerializer},
        tags=["App Profiles"]
    ),
    patch=extend_schema(
        operation_id="finance_profile_partial_update",
        summary="Update app profile",
        description="Update mutable profile settings (for example, spend accounts/base currency).\n"
                    "The reserved `unknown` source cannot be selected as a spend account.",
        request=AppProfileUpdateSerializer,
        responses={
            status.HTTP_200_OK: AppProfileUpdateSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["App Profiles"]
    )
)
class AppProfileView(APIView):
    serializer_class = AppProfileGetSerializer
    """
    App profile view.
    """
    def get(self, request):
        uid = request.user.appprofile.user_id
        result = user_svc.user_get_info(uid=uid)
        serializer = AppProfileGetSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        uid = request.user.appprofile.user_id
        result = user_svc.user_update(
            uid=uid,
            data=request.data
        )
        serializer = AppProfileUpdateSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_profile_snapshot",
        summary="Retrieve profile snapshot",
        description="Retrieve calculated totals and snapshot data for the app profile.",
        responses={status.HTTP_200_OK: SnapshotSerializer},
        tags=["App Profiles"]
    )
)
class AppProfileSnapshotView(APIView):
    serializer_class = SnapshotSerializer
    """
    Snapshot totals view.
    """
    def get(self, request):
        uid = request.user.appprofile.user_id
        result = user_svc.user_get_totals(uid=uid, **request.query_params.dict())
        serializer = SnapshotSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

