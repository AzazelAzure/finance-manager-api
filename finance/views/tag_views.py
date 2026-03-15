from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view

# Service Imports
import finance.services.tag_services as tag_svc

# Serializer Imports
from finance.api_tools.serializers.tag_serializers import(
    TagSerializer,
    TagSetSerializer,
    TagSetReturnSerializer
)



@extend_schema_view(    
    post=extend_schema(
        summary="Add a tag",
        description="Adds a tag to the user's account.\n"  
                    "Allows for multiple tags to be created at once.\n"
                    "Tags are automatically generated when a transaction is created if a tag is assigned and not found.",
        request=TagSerializer,
        responses={status.HTTP_201_CREATED: TagSerializer(many=True)},
        tags=["Tags"]
    ),
    get=extend_schema(
        summary="Retrieve tags",
        description="Retrieves a list of tags for a user.",
        responses={status.HTTP_200_OK: TagSerializer(many=True)},
        tags=["Tags"]
    ),
    patch=extend_schema(
        summary="Not allowed.",
        description="Not allowed for consistency and redundancy.\n"
                    "Tags are single names, making patch and put exactly the same.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["Tags"]
    ),
    put=extend_schema(
        summary="Update a tag",
        description="Updates an existing tag identified by its name.",
        request=TagSerializer,
        responses={status.HTTP_200_OK: TagSerializer(many=True)},
        tags=["Tags"]
    ),
    delete=extend_schema(
        summary="Delete a tag",
        description="Deletes an existing tag identified by its name.",
        responses={status.HTTP_200_OK: TagSerializer(many=True)},
        tags=["Tags"]
    )
)
class TagView(APIView):
    """
    View for tags.

    Attributes:
        post: Add a tag.
        get: Retrieve tags.
        patch: Not allowed.
        put: Update a tag.
        delete: Delete a tag.
    """
    def post(self, request):
        # Check if single and make a list
        if not isinstance(request.data['tags'], list):
            request.data['tags'] = [request.data['tags']] # May need to fix this
        serializer = TagSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        # Add tags
        result = tag_svc.add_tags(
            uid=request.user.appprofile.user,
            data=serializer.data
        )
        
        # Serialize and return
        serializer = TagSerializer(result['added'],many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        # Get tags, serialize, return
        result = tag_svc.get_tags(uid=request.user.appprofile.user)
        serializer = TagSerializer(result['tags'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    def put(self, request):
        # Change name of tag, serialize, return
        serializer = TagSetSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        result = tag_svc.update_tag(
            uid=request.user.appprofile.user,
            data=serializer.data
        )
        serializer = TagSetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    
    def delete(self, request):
        # Delete tag, serialize, return
        serializer = TagSetSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        result = tag_svc.delete_tag(
            uid=request.user.appprofile.user,
            data=serializer.data
        )
        serializer = TagSetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
