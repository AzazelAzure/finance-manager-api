"""User account API view endpoints (create/read/password update/delete)."""
# Django imports
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes



# Serializer Imports
from finance.api_tools.serializers.base_serializers import UserSerializer, PasswordChangeSerializer


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
        description="Update password for the authenticated user. Requires current password verification.",
        request=PasswordChangeSerializer,
        responses={
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    ),
    delete=extend_schema(
        summary="Delete current user",
        description="Delete the authenticated user account. Requires password verification. This action is permanent.",
        request=PasswordChangeSerializer, # Reusing serializer for password field, though we only need password
        responses={
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
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

        # Create user (use validated_data: write_only fields like password are omitted from .data)
        vd = serializer.validated_data
        user = User.objects.create_user(
            username=vd["username"],
            email=vd["user_email"],
            password=vd["password"],
        )
        return Response({'message': "User created successfully"}, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        # Do not pass request.user to Serializer(data=...) — that expects a dict-like payload, not a User instance.
        return Response({"email": request.user.email}, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': "Password updated successfully"}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({'message': "Password verification failed."}, status=status.HTTP_403_FORBIDDEN)
            
        user = request.user
        user.delete()
        return Response({'message': "User deleted successfully"}, status=status.HTTP_200_OK)
    

