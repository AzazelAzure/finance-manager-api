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
        summary="Create categories",
        description="Create one category object.",
        request=CategorySerializer,
        responses={status.HTTP_201_CREATED: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    get=extend_schema(
        summary="List categories",
        description="List all categories for the authenticated user.",
        responses={status.HTTP_200_OK: CategorySerializer(many=True)},
        tags=["Categories"],
    ),
    patch=extend_schema(
        summary="Rename a category",
        description="Partially update a category name by path parameter.",
        request=CategorySerializer,
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    put=extend_schema(
        summary="Replace category payload",
        description="Update category name by path parameter.",
        request=CategorySerializer,
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
    delete=extend_schema(
        summary="Delete category",
        description="Delete category by path parameter.",
        responses={status.HTTP_200_OK: CategorySetReturnSerializer},
        tags=["Categories"],
    ),
)
class CategoryView(APIView):
    
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.add_category(
            request.user.appprofile.user_id,
            serializer.validated_data,
        )
        serializer = CategorySetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, cat_name: str = None):
        if cat_name:
            result = cat_svc.get_category(request.user.appprofile.user_id, cat_name)
            serializer = CategorySerializer(result["category"])
            return Response(serializer.data, status=status.HTTP_200_OK)
        result = cat_svc.get_categories(request.user.appprofile.user_id)
        serializer = CategorySerializer(result["categories"], many=True)
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