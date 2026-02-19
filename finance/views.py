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

    def get(self, request, tx_id: str = None):
        uid = request.user.appprofile.user_id
        
        if tx_id: # If tx_id is provided in the URL path, get a single transaction
            result = svc.user_get_transaction(uid=uid, tx_id=tx_id)
            return Response(result, status=200)
        
        # Otherwise, handle dynamic filtering for a list of transactions
        filter_params = {
            'tx_type': request.query_params.get('tx_type'),
            'tag_name': request.query_params.get('tag_name'),
            'category': request.query_params.get('category'),
            'source': request.query_params.get('source'),
            'currency_code': request.query_params.get('currency_code'),
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'current_month': request.query_params.get('current_month'), # Check for presence, e.g., ?current_month=true
        }
        
        # Remove None values to avoid passing them to the service function if not provided
        filter_params = {k: v for k, v in filter_params.items() if v is not None}

        result = svc.user_get_transactions(uid=uid, **filter_params)
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