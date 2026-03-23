from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view

# Service Imports
import finance.services.tag_services as tag_svc

# Serializer Imports
from finance.api_tools.serializers.tag_serializers import(
    TagSerializer,
    TagPatchPutSerializer,
    TagSetReturnSerializer,
)



@extend_schema_view(    
    post=extend_schema(
        summary="Add a tag",
        description="Add one or more tags.\n"
                    "Tags are stored as lowercase values and duplicates are rejected.",
        request=TagSerializer,
        responses={status.HTTP_201_CREATED: TagSetReturnSerializer},
        tags=["Tags"]
    ),
    get=extend_schema(
        summary="Retrieve tags",
        description="Retrieves a list of tags for a user.",
        responses={status.HTTP_200_OK: TagSerializer(many=True)},
        tags=["Tags"]
    ),
    patch=extend_schema(
        summary="Partially update tag names",
        description="Rename and/or delete tags using a mapping object under `tags`.",
        request=TagPatchPutSerializer,
        responses={status.HTTP_200_OK: TagSetReturnSerializer},
        tags=["Tags"]
    ),
    put=extend_schema(
        summary="Update tag names",
        description="Update tags using the same payload format as PATCH.",
        request=TagPatchPutSerializer,
        responses={status.HTTP_200_OK: TagSetReturnSerializer},
        tags=["Tags"]
    ),
    delete=extend_schema(
        summary="Delete tags",
        description="Delete one or more tags from payload mapping.",
        request=TagPatchPutSerializer,
        responses={status.HTTP_200_OK: TagSetReturnSerializer},
        tags=["Tags"]
    )
)
class TagView(APIView):
    """
    View for tags.

    Attributes:
        post: Add a tag.
        get: Retrieve tags.
        patch: Partially update tags.
        put: Update a tag.
        delete: Delete a tag.
    """
    def post(self, request):
        payload = dict(request.data)
        if not isinstance(payload.get("tags"), list):
            payload["tags"] = [payload.get("tags")]
        serializer = TagSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        # Add tags
        result = tag_svc.add_tags(
            uid=request.user.appprofile.user_id,
            data=serializer.validated_data,
        )
        
        # Serialize and return
        serializer = TagSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        # Get tags, serialize, return
        result = tag_svc.get_tags(uid=request.user.appprofile.user_id)
        serializer = TagSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        serializer = TagPatchPutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = tag_svc.update_tag(
            uid=request.user.appprofile.user_id,
            data=serializer.validated_data,
        )
        serializer = TagSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        # Change name of tag, serialize, return
        serializer = TagPatchPutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = tag_svc.update_tag(
            uid=request.user.appprofile.user_id,
            data=serializer.validated_data,
        )
        serializer = TagSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    
    def delete(self, request):
        # Delete tag, serialize, return
        serializer = TagPatchPutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = tag_svc.delete_tag(
            uid=request.user.appprofile.user_id,
            data=serializer.validated_data,
        )
        serializer = TagSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
