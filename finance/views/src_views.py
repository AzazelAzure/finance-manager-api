from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

# Service Imports
import finance.services.source_services as src_svc

# Serializer Imports
from finance.api_tools.serializers.src_serializers import(
    SourceSerializer,
    SourcePostSerializer,
    SourceSetReturnSerializer
)



@extend_schema_view(
    post=extend_schema(
        summary="Add a payment source",
        description="Adds a payment source to the user's account.\n"
                    "Allows for multiple sources to be created at once.\n"
                    "Forbidden to add 'unknown' source as that is a default empty source.\n"
                    "If forbidden, will return HTTP 400 Bad Request during creation and not add any sources.",
        request=SourceSerializer,
        responses={status.HTTP_201_CREATED: SourceSerializer},
        tags=["Sources"]
    ),
    get=extend_schema(
        summary="Retrieve sources",
        description="Retrieves a list of payment sources for a user.  Accepts optional filters.",
        parameters=[
            OpenApiParameter(name='acc_type', type=OpenApiTypes.STR, description='Filter by account type (e.g., CASH, INVESTMENT, SAVINGS)'),
            OpenApiParameter(name='source', type=OpenApiTypes.STR, description='Filter by source (e.g., VISA, MASTERCARD, AMEX)'),
        ],
        responses={status.HTTP_200_OK: SourceSerializer(many=True)},
        tags=["Sources"]
    ),
    patch=extend_schema(
        summary="Not allowed.",
        description="For financial fidelity, this endpoint is not allowed.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["Sources"]
    ),
    put=extend_schema(
        summary="Update a payment source",
        description="Updates an existing payment source identified by its source.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.",
        request=SourceSerializer,
        responses={
            status.HTTP_200_OK: SourceSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    ),
    delete=extend_schema(
        summary="Delete a payment source",
        description="Deletes an existing payment source identified by its source.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.",
        responses={
            status.HTTP_200_OK: SourceSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    )
)
class SourceView(APIView):
    """
    View for payment sources.\n
    Disallows patch methods for financial fidelity.

    Attributes:
        post: Add a payment source.
        get: Retrieve sources.
        patch: Not allowed.
        put: Update a payment source.
        delete: Delete a payment source.
    """
    def post(self, request):
        # Check if single or list of sources and serialize
        is_many = isinstance(request.data, list)
        serializer = SourcePostSerializer(request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Handle Sources based of list or single
        if is_many:
            result = src_svc.bulk_add_sources(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        else:
            result = src_svc.add_source(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        
        # Serialize and return
        serializer = SourceSetReturnSerializer(result['added'], many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def put(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    def get(self, request):
        # Get sources, filter by params, serialize, return
        result = src_svc.get_sources(uid=request.user.appprofile.user, **request.query_params)
        serializer = SourceSerializer(result['sources'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, src: str):
        if src.lower() == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.update_source(
            uid=request.user.appprofile.user_id,
            source=src,
            data=request.data
        )
        serializer = SourceSetReturnSerializer(result['updated'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        if request.data['source'] == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.delete_source(
            uid=request.user.appprofile.user,
            source=request.data['source']
        )
        serializer = SourceSetReturnSerializer(result['deleted'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
