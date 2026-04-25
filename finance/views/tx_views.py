import copy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

# Service Imports
import finance.services.transaction_services as tx_svc

# Serializer Imports
from finance.api_tools.serializers.tx_serializers import(
    TransactionSerializer,
    TransactionSetSerializer,
    TransactionSetReturnSerializer,
    TransactionGetSerializer,
    TransactionGetReturnSerializer
)
@extend_schema_view(
    post=extend_schema(
        summary="Create one or more transactions",
        description="Create a single transaction object or a list of transaction objects.\n"
                    "Amounts are normalized by type (EXPENSE/XFER_OUT negative; INCOME/XFER_IN positive).\n"
                    "Client-supplied `tx_id` and `entry_id` are rejected.",
        request=TransactionSetSerializer,
        responses={
            status.HTTP_201_CREATED: TransactionSetReturnSerializer,
            status.HTTP_403_FORBIDDEN: None,
            }, 
        tags=["Transactions"]
    ),
    get=extend_schema(
        summary="Retrieve transactions",
        description="Retrieve transactions with optional filtering.\n"
                    "When no filters are provided, the most recent transaction is returned by service logic.\n"
                    "Aggregate totals are included in the response payload.",
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
            status.HTTP_200_OK: TransactionGetReturnSerializer,
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
        description="Partially update a transaction by `tx_id`.\n"
                    "`tx_id` and `entry_id` are immutable and rejected.\n"
                    "A `date` field is required by this view before forwarding to the service layer.",
        request=TransactionSetSerializer,
        responses={
            status.HTTP_200_OK: TransactionSetReturnSerializer,
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Transactions"]
    ),
    delete=extend_schema(
        summary="Delete a transaction",
        description="Delete an existing transaction by `tx_id`.",
        responses={status.HTTP_200_OK: TransactionGetSerializer},
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
        data = copy.deepcopy(request.data)
        self._normalize_tags_to_list(data, many=is_many)
        serializer = TransactionSetSerializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        check = self._txset_check(serializer.data)
        if isinstance(check, Response):
            return check
        
        # Handle Transactions based of list or single
        result = tx_svc.add_transaction(
            request.user.appprofile.user_id,
            serializer.data,
        )
            
        # Serialize and return
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, tx_id: str = None):
        uid = request.user.appprofile.user_id
        
        if tx_id: # If tx_id is provided in the URL path, get a single transaction
            result = tx_svc.get_transaction(uid, tx_id)
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
        result = tx_svc.get_transactions(uid, **filter_params)
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
            request.user.appprofile.user_id,
            tx_id,
            request.data,
        )
        
        # Serialize and return
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def put(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def delete(self, request, tx_id: str):
        # Delete transaction
        result = tx_svc.delete_transaction(
            request.user.appprofile.user_id,
            tx_id,
        )
        
        # Serialize from the in-memory instance returned by the service (row may already be deleted)
        serializer = TransactionGetSerializer(result['deleted'])
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @staticmethod
    def _normalize_tags_to_list(data, many=False):
        """Ensure 'tags' is a list for each item so serializer ListField accepts it."""
        if many:
            for item in data:
                if item.get('tags') is not None and not isinstance(item['tags'], list):
                    item['tags'] = [item['tags']]
        else:
            if data.get('tags') is not None and not isinstance(data['tags'], list):
                data['tags'] = [data['tags']]

    @staticmethod
    def _txset_check(data):
        """Reject immutable identity fields and normalize scalar tags to list."""
        if isinstance(data, list):
            for item in data:
                if item.get('tags'):
                    if not isinstance(item['tags'], list):
                        item['tags'] = [item['tags']]
                if item.get('tx_id'):
                    return Response(status=status.HTTP_403_FORBIDDEN)
                if item.get('entry_id'):
                    return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            if data.get('tags'):
                if not isinstance(data['tags'], list):
                    data['tags'] = [data['tags']]
            if data.get('tx_id'):
                return Response(status=status.HTTP_403_FORBIDDEN)
            if data.get('entry_id'):
                return Response(status=status.HTTP_403_FORBIDDEN)
        return data


