from rest_framework.views import APIView
from rest_framework.response import Response
from .api_tools.serializers import TransactionSerializer, SourceSerializer, AssetSerializer
import finance.services.services as svc

class TransactionView(APIView):
    def post(self, request):
        is_many = isinstance(request.data, list)
        serializer = TransactionSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        if is_many:
            result = svc.user_add_bulk_transactions(
                data=serializer.data,
                uid=request.user.appprofile.user_id)
        else:
            result = svc.user_add_transaction(
                data=serializer.data,
                uid=request.user.appprofile.user_id)
        return Response(result, status=200)

    def get_all_transactions(self, request):
        result = svc.user_get_transactions(
            uid=request.user.appprofile.user_id)
        return Response(result, status=200)

    def get_transaction(self, request, tx_id: str):
        result = svc.user_get_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id)
        return Response(result, status=200)

    def put(self, request, tx_id: str):
        result = svc.user_update_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id,
            data=request.data)
        return Response(result, status=200)

    def delete(self, request, tx_id: str):
        result = svc.user_delete_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id)
        return Response(result, status=200)

class AssetView(APIView):
    def post(self, request):
        serializer = AssetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = svc.user_add_asset(
            data=serializer.data,
            uid=request.user.appprofile.user_id)
        return Response(result, status=200)