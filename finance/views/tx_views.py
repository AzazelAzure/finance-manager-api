from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

# Service Imports
import finance.services.transaction_services as tx_svc

# Serializer Imports
from api_tools.serializers.tx_serializers import(
    TransactionSerializer,
    TransactionSetSerializer,
    TransactionSetReturnSerializer,
    TransactionGetSerializer,
    TransactionGetReturnSerializer
)
from api_tools.serializers.spectactular_serializers import SpectacularTxSerializer

@extend_schema_view(
    post=extend_schema(
        summary="Create one or more transactions",
        description="Allows creation of a single transaction or a list of transactions.\n"
                    "Transaction amounts are automically fixed by transaction type.\n"
                    "For example, EXPENSE and XFER_OUT transactions are fixed to negative, and INCOME and XFER_IN transactions are fixed to positive.\n"
                    "Allows for 0 value transactions.\n"
                    "Transaction ids and entry ids are auto generated, and cannot be set.\n"
                    "Will return HTTP 403 Forbidden if either is set.",
        request=TransactionSerializer,
        responses={
            status.HTTP_201_CREATED: TransactionSerializer,
            status.HTTP_403_FORBIDDEN: None,
            }, 
        tags=["Transactions"]
    ),
    get=extend_schema(
        summary="Retrieve transactions",
        description="Retrieves a single transaction by ID or a list of transactions with optional filters.\n"
                    "If month is set with no year, will return transactions for current month.\n"
                    "If start_date is set with no end_date, will return all transactions after start_date.\n"
                    "If end_date is set with no start_date, will return all transactions before end_date.\n",
        parameters=[
            OpenApiParameter(name='tx_type', type=OpenApiTypes.STR, description='Filter by transaction type (e.g., EXPENSE, INCOME)'),
            OpenApiParameter(name='tag_name', type=OpenApiTypes.STR, description='Filter by tag name'),
            OpenApiParameter(name='category', type=OpenApiTypes.STR, description='Filter by category'),
            OpenApiParameter(name='source', type=OpenApiTypes.STR, description='Filter by source'),
            OpenApiParameter(name='currency_code', type=OpenApiTypes.STR, description='Filter by currency code'),
            OpenApiParameter(name='start_date', type=OpenApiTypes.STR, description='Filter by start date'),
            OpenApiParameter(name='end_date', type=OpenApiTypes.STR, description='Filter by end date'),
            OpenApiParameter(name='current_month', type=OpenApiTypes.BOOL, description='Filter by current month'),
            OpenApiParameter(name='month', type=OpenApiTypes.INT, description='Filter by month'),
            OpenApiParameter(name='year', type=OpenApiTypes.INT, description='Filter by year'),
            OpenApiParameter(name='last_month', type=OpenApiTypes.BOOL, description='Filter by last month'),
            OpenApiParameter(name='previous_week', type=OpenApiTypes.BOOL, description='Filter by previous week'),
            OpenApiParameter(name='date', type=OpenApiTypes.STR, description='Filter by date'),
            OpenApiParameter(name='gte', type=OpenApiTypes.INT, description='Filter by greater than or equal to'),
            OpenApiParameter(name='lte', type=OpenApiTypes.INT, description='Filter by less than or equal to'),
            OpenApiParameter(name='by_year', type=OpenApiTypes.INT, description='Filter by year'),
            OpenApiParameter(name='by_date', type=OpenApiTypes.STR, description='Filter by date'),
        ],
        responses={
            status.HTTP_200_OK: SpectacularTxSerializer,
            status.HTTP_200_OK: TransactionGetSerializer
            },
        tags=["Transactions"]
    ),
    put=extend_schema(
        summary="Not allowed.",
        description="For transactional fidelity, this endpoint is not allowed.",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["Transactions"]
    ),
    patch=extend_schema(
        summary="Update a transaction",
        description="Updates an existing transaction identified by its ID.\n"
                    "Forbidden for 'tx_id' and 'entry_id' as they are auto generated unique identifiers.  These cannot be changed.\n"
                    "If no date is provided, will return HTTP 400 Bad Request.\n" 
                    "This is to prevent accidentally changing the date to date of transaction.",
        request=TransactionSerializer,
        responses={
            status.HTTP_200_OK: TransactionSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Transactions"]
    ),
    delete=extend_schema(
        summary="Delete a transaction",
        description="Deletes an existing transaction identified by its ID.",
        responses={status.HTTP_200_OK: TransactionSerializer(many=True)},
        tags=["Transactions"]
    )
)
class TransactionView(APIView):
    """
    View for transactions.\n 
    Disallows put methods for financial fidelity.

    Attributes:
        post: Create one or more transactions.
        get: Retrieve transactions.
        put: Update a transaction.
        patch: Not allowed.
        delete: Delete a transaction.
    """
    def post(self, request):
        # Check if single or list of transactions and serialize
        is_many = isinstance(request.data, list)
        serializer = TransactionSetSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        check = self._txset_check(serializer.data)
        if isinstance(check, Response):
            return check
        
        # Handle Transactions based of list or single
        result = tx_svc.add_transaction(
            data=serializer.data,
            uid=request.user.appprofile.user_id)
            
        # Serialize and return
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, tx_id: str = None):
        uid = request.user.appprofile.user_id
        
        if tx_id: # If tx_id is provided in the URL path, get a single transaction
            result = tx_svc.get_transaction(uid=uid, tx_id=tx_id)
            serializer = TransactionGetSerializer(result['transaction'])
            return Response({'transaction': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)
        
        # Otherwise, handle dynamic filtering for a list of transactions
        filter_params = {
            'tx_type': request.query_params.get('tx_type'),
            'tag_name': request.query_params.get('tag_name'),
            'category': request.query_params.get('category'),
            'source': request.query_params.get('source'),
            'currency_code': request.query_params.get('currency_code'),
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'current_month': request.query_params.get('current_month'),
            'month': request.query_params.get('month'),
            'year': request.query_params.get('year'),
            'last_month': request.query_params.get('last_month'),
            'previous_week': request.query_params.get('previous_week'),
            'date': request.query_params.get('date'),
            'gte': request.query_params.get('gte'),
            'lte': request.query_params.get('lte'),
            'by_year': request.query_params.get('by_year'),
            'by_date': request.query_params.get('by_date'),
        }
        
        # Remove None values to avoid passing none to the service function if not provided
        filter_params = {k: v for k, v in filter_params.items() if v is not None}
        
        # If no filters are provided, returns most recent transaction
        result = tx_svc.get_transactions(uid=uid, **filter_params)
        serializer = TransactionGetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, tx_id: str):
        # Fix tags and reject altering tx_id
        check = self._txset_check(request.data)
        if isinstance(check, Response):
            return check
        

        if not request.data.get('date'):
            return Response(status=status.HTTP_400_BAD_REQUEST)


        # Update transaction
        result = tx_svc.update_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id,
            data=request.data)
        
        # Serialize and return
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def delete(self, request, tx_id: str):
        # Delete transaction
        result = tx_svc.delete_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id)
        
        # Serialize and return
        serializer = TransactionGetSerializer(data=result['deleted'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @staticmethod
    def _txset_check(data):
        if isinstance(data, list):
            for item in data:
                if item.get('tags'):
                    if not isinstance(item['tags'], list):
                        item['tags'] = [item['tags']]
                if item.get('tx_id'):
                    return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            if data.get('tags'):
                if not isinstance(data['tags'], list):
                    data['tags'] = [data['tags']]
                if data.get('tx_id'):
                    return Response(status=status.HTTP_403_FORBIDDEN)
        return data


