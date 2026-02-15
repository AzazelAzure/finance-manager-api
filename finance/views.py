from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import TransactionSerializer
import finance.services as svc

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