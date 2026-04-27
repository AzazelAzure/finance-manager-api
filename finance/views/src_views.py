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
        operation_id="finance_sources_create",
        summary="Add a payment source",
        description="Create one source object or a list of source objects.\n"
                    "The reserved source name `unknown` is rejected by validation.",
        request=SourcePostSerializer,
        responses={status.HTTP_201_CREATED: SourceSetReturnSerializer},
        tags=["Sources"]
    ),
    get=extend_schema(
        operation_id="finance_sources_list",
        summary="Retrieve sources list",
        description="Retrieves a list of payment sources for a user. Accepts optional filters.",
        parameters=[
            OpenApiParameter(name='acc_type', type=OpenApiTypes.STR, description='Filter by account type (e.g., CASH, INVESTMENT, SAVINGS)'),
            OpenApiParameter(name='source', type=OpenApiTypes.STR, description='Filter by source (e.g., VISA, MASTERCARD, AMEX)'),
        ],
        responses={status.HTTP_200_OK: SourceSerializer(many=True)},
        tags=["Sources"]
    )
)
class SourceListCreateView(APIView):
    serializer_class = SourcePostSerializer
    
    def post(self, request):
        is_many = isinstance(request.data, list)
        serializer = SourcePostSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        result = src_svc.add_source(
            request.user.appprofile.user_id,
            serializer.data,
        )
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        result = src_svc.get_sources(request.user.appprofile.user_id, **request.query_params.dict())
        serializer = SourceSerializer(result["sources"], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_sources_retrieve",
        summary="Retrieve source",
        description="Retrieve a single source by its name.",
        responses={status.HTTP_200_OK: SourceSerializer},
        tags=["Sources"]
    ),
    patch=extend_schema(
        operation_id="finance_sources_partial_update",
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
        operation_id="finance_sources_update",
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
        operation_id="finance_sources_destroy",
        summary="Delete a payment source",
        description="Delete an existing source.\n"
                    "The reserved source name `unknown` cannot be deleted.",
        responses={
            status.HTTP_200_OK: SourceSetReturnSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    )
)
class SourceDetailView(APIView):
    serializer_class = SourcePutSerializer

    def get(self, request, source: str):
        result = src_svc.get_source(request.user.appprofile.user_id, source)
        serializer = SourceSerializer(result["source"])
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
    
    def delete(self, request, source: str):
        if source.lower() == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.delete_source(
            request.user.appprofile.user_id,
            source,
        )
        serializer = SourceSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
