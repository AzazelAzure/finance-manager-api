"""
This module defines all views for the finance manager application.

Attributes:
    TransactionView: View for transactions.
    SourceView: View for sources.
    UpcomingExpenseView: View for upcoming expenses.
    TagView: View for tags.
    AppProfileView: View for app profiles.
    UserView: View for users.
"""
# Django imports
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes



# Serializer Imports
from finance.api_tools.serializers.base_serializers import UserSerializer


# TODO: Add documentation
# TODO: Add logging
# TODO: Fix extend schemas to look better/more professional.
    # use description = textwrap.dedent("""example""") and markdown

# TODO: Add views for each URL to fix routing issues

@extend_schema_view(
    post=extend_schema(
        summary="Create one or more users",
        description="Allows creation of a single user or a list of users.",
        request=UserSerializer,
        responses={status.HTTP_201_CREATED: OpenApiTypes.OBJECT}, 
        tags=["Users"]
    ),
    get=extend_schema(
        summary="Retrieves users email.",
        description="Retrieves the email for the currently logged in user.",
        responses={status.HTTP_200_OK: OpenApiTypes.OBJECT},
        tags=["Users"]
    ),
    patch=extend_schema(
        summary="Update a user",
        description="Updates an existing user identified by its username and password.  Used to update password.",
        request=UserSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    ),
    delete=extend_schema(
        summary="Delete a user",
        description="Deletes an existing user identified by its username.",
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    )
)
class UserView(APIView):
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
    

