from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view


import finance.services.category_services as cat_svc
from finance.api_tools.serializers.cat_serializers import(
    CategorySerializer,
    CategorySetReturnSerializer,
)

@extend_schema_view(
    post=extend_schema(
        operation_id="finance_categories_create",
        summary="Create categories",
        description="Create one category object.",
        request=CategorySerializer,
        responses={status.HTTP_201_CREATED: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    get=extend_schema(
        operation_id="finance_categories_list",
        summary="List categories",
        description="List all categories for the authenticated user.",
        responses={status.HTTP_200_OK: CategorySerializer(many=True)},
        tags=["Categories"],
    )
)
class CategoryListCreateView(APIView):
    serializer_class = CategorySerializer
    
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.add_category(
            request.user.appprofile.user_id,
            serializer.validated_data,
        )
        serializer = CategorySetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        result = cat_svc.get_categories(request.user.appprofile.user_id)
        serializer = CategorySerializer(result["categories"], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_categories_retrieve",
        summary="Retrieve category",
        description="Retrieve a single category by its name.",
        responses={status.HTTP_200_OK: CategorySerializer},
        tags=["Categories"],
    ),
    patch=extend_schema(
        operation_id="finance_categories_partial_update",
        summary="Rename a category",
        description="Partially update a category name by path parameter.",
        request=CategorySerializer,
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    put=extend_schema(
        operation_id="finance_categories_update",
        summary="Replace category payload",
        description="Update category name by path parameter.",
        request=CategorySerializer,
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    delete=extend_schema(
        operation_id="finance_categories_destroy",
        summary="Delete category",
        description="Delete category by path parameter.",
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
)
class CategoryDetailView(APIView):
    serializer_class = CategorySerializer

    def get(self, request, cat_name: str):
        result = cat_svc.get_category(request.user.appprofile.user_id, cat_name)
        serializer = CategorySerializer(result["category"])
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, cat_name: str):
        serializer = CategorySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.update_category(
            request.user.appprofile.user_id,
            cat_name,
            serializer.validated_data,
        )
        serializer = CategorySetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, cat_name: str):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.update_category(
            request.user.appprofile.user_id,
            cat_name,
            serializer.validated_data,
        )
        serializer = CategorySetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, cat_name: str):
        result = cat_svc.delete_category(
            request.user.appprofile.user_id,
            cat_name,
        )
        serializer = CategorySetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)