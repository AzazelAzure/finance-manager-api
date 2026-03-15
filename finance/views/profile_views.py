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
        summary="Not allowed.",
        description="All app profiles are generated automatically.  This endpoint is not allowed. Automatically generated on user creation.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["App Profiles"]
    ),
    get=extend_schema(
        summary="Retrieve app profile",
        description="Retrieves the spend accounts and base currency for a user.",
        responses={status.HTTP_200_OK: AppProfileGetSerializer(many=True)},
        tags=["App Profiles"]
    ),
    patch=extend_schema(
        summary="Update app profile",
        description="Updates the spend accounts and base currency for a user.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.  This cannot be used as spend account.",
        request=AppProfileGetSerializer,
        responses={
            status.HTTP_200_OK: AppProfileGetSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["App Profiles"]
    ),
    put=extend_schema(
        summary="Not allowed.",
        description="Not allowed as only fields that can be updated for user are spend accounts and base currency.\n",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["App Profiles"]
    ),
    delete=extend_schema(
        summary="Not allowed.",
        description="All app profiles are generated automatically.  This endpoint is not allowed. To delete, delete the user account.",
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
            serializer = SnapshotSerializer(result, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Return the app profile.  Only returns spend account and base currency.
        result = user_svc.user_get_info(uid=uid)
        serializer = AppProfileGetSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        uid = request.user.appprofile.user_id
        result = user_svc.user_update_info(
            uid=uid,
            data=request.data
        )
        serializer = AppProfileUpdateSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def delete(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

