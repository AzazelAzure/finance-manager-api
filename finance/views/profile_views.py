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
    post=extend_schema(
        summary="Not allowed",
        description="App profiles are auto-created alongside users; manual creation is disabled.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["App Profiles"]
    ),
    get=extend_schema(
        summary="Retrieve app profile",
        description="Retrieve profile settings. Snapshot totals are available on the snapshot route.",
        responses={status.HTTP_200_OK: AppProfileGetSerializer},
        tags=["App Profiles"]
    ),
    patch=extend_schema(
        summary="Update app profile",
        description="Update mutable profile settings (for example, spend accounts/base currency).\n"
                    "The reserved `unknown` source cannot be selected as a spend account.",
        request=AppProfileUpdateSerializer,
        responses={
            status.HTTP_200_OK: AppProfileUpdateSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["App Profiles"]
    ),
    put=extend_schema(
        summary="Not allowed",
        description="Only partial updates are supported on this resource.",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["App Profiles"]
    ),
    delete=extend_schema(
        summary="Not allowed",
        description="Profiles are lifecycle-managed with users; delete the user account instead.",
        responses={status.HTTP_501_NOT_IMPLEMENTED: None},
        tags=["App Profiles"]
    )
)
class AppProfileView(APIView):
    """
    App profile view.

    Attributes:
        post: Not allowed.
        get: Retrieve app profile.
        patch: Update app profile.
        put: Not allowed
        delete: Not allowed.
    """
    def post(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def get(self, request, snapshot: bool = False):
        uid = request.user.appprofile.user_id
        # Return the snapshot if requested, otherwise return the app profile
        if snapshot:
            result = user_svc.user_get_totals(uid=uid)
            serializer = SnapshotSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Return the app profile.  Only returns spend account and base currency.
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
        

    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def delete(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

