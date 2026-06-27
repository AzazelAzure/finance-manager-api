"""User account API view endpoints (create/read/password update/delete)."""
# Django imports
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import BasePermission
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiTypes



# Serializer Imports
from finance.api_tools.serializers.base_serializers import UserSerializer, PasswordChangeSerializer


class IsAuthenticatedOrCreateOnly(BasePermission):
    """Allow open signup while requiring auth for account operations."""

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        return bool(request.user and request.user.is_authenticated)


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
    permission_classes = [IsAuthenticatedOrCreateOnly]

    def post(self, request):
        # Get user model
        User = get_user_model()

        # Check if all user credentials provided
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user (use validated_data: write_only fields like password are omitted from .data)
        vd = serializer.validated_data
        username = vd["username"].strip()
        email = vd["user_email"].strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"username": ["This username is already taken."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {
                    "user_email": [
                        "This email is already registered. Sign in instead.",
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=vd["password"],
            )
        except IntegrityError:
            return Response(
                {
                    "user_email": [
                        "This email is already registered. Sign in instead.",
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile = user.appprofile
        profile.tos_version = vd["tos_version"]
        profile.tos_accepted_at = vd["tos_accepted_at"]
        profile.save(update_fields=["tos_version", "tos_accepted_at"])
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
    

