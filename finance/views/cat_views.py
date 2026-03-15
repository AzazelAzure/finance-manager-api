from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes


import finance.services.category_services as cat_svc
from finance.api_tools.serializers.cat_serializers import(
    CategorySerializer,
    CategorySetReturnSerializer,
    CategoryGetReturnSerializer
)

# TODO Extend schemas, Docstrings, Code Comments

class CategoryView(APIView):
    
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.add_category(
            uid=request.user.appprofile.user,
            data=serializer.data
        )
        serializer = CategorySetReturnSerializer(result['added'], many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, cat_name: str = None):
        if cat_name:
            result = cat_svc.get_category(uid=request.user.appprofile.user, cat_name=cat_name)
            serializer = CategorySerializer(result['category'])
            return Response(serializer.data, status=status.HTTP_200_OK)
        result = cat_svc.get_categories(uid=request.user.appprofile.user)
        serializer = CategorySerializer(result['categories'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def patch(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def put(self, request, cat_name: str):
        serializer = CategorySerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        result = cat_svc.update_category(
            uid=request.user.appprofile.user,
            cat_name=cat_name,
            data=serializer.data
        )
        serializer = CategorySetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, cat_name: str):
        result = cat_svc.delete_category(
            uid=request.user.appprofile.user,
            cat_name=cat_name
        )
        serializer = CategorySetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)