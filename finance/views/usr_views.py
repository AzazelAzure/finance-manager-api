"""User account API view endpoints (create/read/password update/delete)."""
# Django imports
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes



# Serializer Imports
from finance.api_tools.serializers.base_serializers import UserSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Create one or more users",
        description="Create a user account from username/email/password payload.",
        request=UserSerializer,
        responses={status.HTTP_201_CREATED: OpenApiTypes.OBJECT}, 
        tags=["Users"]
    ),
    get=extend_schema(
        summary="Retrieve current user email",
        description="Return email for the authenticated user.",
        responses={status.HTTP_200_OK: OpenApiTypes.OBJECT},
        tags=["Users"]
    ),
    patch=extend_schema(
        summary="Update current user password",
        description="Update password for the authenticated user. Username must match request user.",
        request=UserSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    ),
    delete=extend_schema(
        summary="Delete current user",
        description="Delete the authenticated user account. Username must match request user.",
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    )
)
class UserView(APIView):
    """APIView for basic authenticated user account operations."""
    def post(self, request):
        # Get user model
        User = get_user_model()

        # Check if all user credentials provided
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user
        user = User.objects.create_user(
            username=serializer.data['username'],
            email=serializer.data['user_email'],
            password=serializer.data['password']
        )
        return Response({'message': "User created successfully"}, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        serialzer = UserSerializer(data=request.user)
        serialzer.is_valid(raise_exception=True)
        return Response({'email': request.user.email}, status=status.HTTP_200_OK)

    def patch(self, request):
        User = get_user_model()
        if request.data['username'] != request.user.username:
            return Response({'message': "Incorrect user."}, status=status.HTTP_403_FORBIDDEN)
        user = User.objects.get(username=request.data['username'])
        user.set_password(request.data['password'])
        user.save()
        return Response({'message': "Password updated successfully"}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        User = get_user_model()
        if request.data['username'] != request.user.username:
            return Response({'message': "Incorrect user."}, status=status.HTTP_403_FORBIDDEN)
        user = User.objects.get(username=request.data['username'])
        user.delete()
        return Response({'message': "User deleted successfully"}, status=status.HTTP_200_OK)
    

