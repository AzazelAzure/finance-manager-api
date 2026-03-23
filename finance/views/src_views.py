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
    SourceSetReturnSerializer,
    SourcePatchSerializer,
    SourcePutSerializer,
)



@extend_schema_view(
    post=extend_schema(
        summary="Add a payment source",
        description="Create one source object or a list of source objects.\n"
                    "The reserved source name `unknown` is rejected by validation.",
        request=SourcePostSerializer,
        responses={status.HTTP_201_CREATED: SourceSetReturnSerializer},
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
        summary="Partially update a payment source",
        description="Patch mutable fields for an existing source.\n"
                    "The reserved source name `unknown` cannot be modified.",
        request=SourcePatchSerializer,
        responses={
            status.HTTP_200_OK: SourceSetReturnSerializer,
            status.HTTP_403_FORBIDDEN: None,
        },
        tags=["Sources"]
    ),
    put=extend_schema(
        summary="Update a payment source",
        description="Replace mutable fields for an existing source.\n"
                    "The reserved source name `unknown` cannot be modified.",
        request=SourcePutSerializer,
        responses={
            status.HTTP_200_OK: SourceSetReturnSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    ),
    delete=extend_schema(
        summary="Delete a payment source",
        description="Delete an existing source passed as `source` in request body.\n"
                    "The reserved source name `unknown` cannot be deleted.",
        responses={
            status.HTTP_200_OK: SourceSetReturnSerializer,
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
        serializer = SourcePostSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Handle Sources based of list or single
        result = src_svc.add_source(
            request.user.appprofile.user_id,
            serializer.data,
        )
        
        # Serialize and return
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, source: str = None):
        if source:
            result = src_svc.get_source(request.user.appprofile.user_id, source)
            serializer = SourceSerializer(result["source"])
            return Response(serializer.data, status=status.HTTP_200_OK)
        result = src_svc.get_sources(request.user.appprofile.user_id, **request.query_params)
        serializer = SourceSerializer(result["sources"], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, source: str):
        if source.lower() == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SourcePatchSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = src_svc.update_source(
            request.user.appprofile.user_id,
            source,
            serializer.validated_data,
            partial=True,
        )
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, source: str):
        if source.lower() == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = SourcePutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = src_svc.update_source(
            request.user.appprofile.user_id,
            source,
            serializer.validated_data,
            partial=False,
        )
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        if request.data.get("source", "").lower() == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.delete_source(
            request.user.appprofile.user_id,
            request.data['source'],
        )
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
