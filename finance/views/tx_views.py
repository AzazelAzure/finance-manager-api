import copy
from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from rest_framework.exceptions import ValidationError

# Service Imports
import finance.services.transaction_services as tx_svc

# Serializer Imports
from finance.api_tools.serializers.tx_serializers import(
    TransactionSerializer,
    TransactionSetSerializer,
    TransactionSetReturnSerializer,
    TransactionGetSerializer,
    TransactionGetReturnSerializer,
    TransactionCalendarReturnSerializer,
    TransactionVisualizationReturnSerializer,
)
class TransactionBaseView(APIView):
    """Base logic shared between transaction views."""
    serializer_class = TransactionSetSerializer

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


@extend_schema_view(
    post=extend_schema(
        operation_id="finance_transactions_create",
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
        operation_id="finance_transactions_list",
        summary="Retrieve transactions list",
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
    )
)
class TransactionListCreateView(TransactionBaseView):
    """View for listing and creating transactions."""

    def post(self, request):
        is_many = isinstance(request.data, list)
        data = copy.deepcopy(request.data)
        self._normalize_tags_to_list(data, many=is_many)
        serializer = TransactionSetSerializer(data=data, many=is_many)
        if not serializer.is_valid():
            from loguru import logger
            logger.warning("transaction_validation_failed | errors={errors} | data={data}", errors=serializer.errors, data=data)
            serializer.is_valid(raise_exception=True)
        check = self._txset_check(serializer.data)
        if isinstance(check, Response):
            return check
        
        result = tx_svc.add_transaction(
            request.user.appprofile.user_id,
            serializer.data,
        )
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        uid = request.user.appprofile.user_id
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
        filter_params = {k: v for k, v in filter_params.items() if v is not None}
        result = tx_svc.get_transactions(uid, **filter_params)
        serializer = TransactionGetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_transactions_retrieve",
        summary="Retrieve a transaction",
        description="Retrieve a single transaction by its `tx_id`.",
        responses={status.HTTP_200_OK: TransactionGetSerializer},
        tags=["Transactions"]
    ),
    patch=extend_schema(
        operation_id="finance_transactions_partial_update",
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
        operation_id="finance_transactions_destroy",
        summary="Delete a transaction",
        description="Delete an existing transaction by `tx_id`.",
        responses={status.HTTP_200_OK: TransactionGetSerializer},
        tags=["Transactions"]
    )
)
class TransactionDetailView(TransactionBaseView):
    """View for retrieving, updating, and deleting a specific transaction."""

    def get(self, request, tx_id: str):
        uid = request.user.appprofile.user_id
        result = tx_svc.get_transaction(uid, tx_id)
        serializer = TransactionGetSerializer(result['transaction'])
        return Response({'transaction': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)
    
    def patch(self, request, tx_id: str):
        check = self._txset_check(request.data)
        if isinstance(check, Response):
            return check
        
        if not request.data.get('date'):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        result = tx_svc.update_transaction(
            request.user.appprofile.user_id,
            tx_id,
            request.data,
        )
        serializer = TransactionSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def delete(self, request, tx_id: str):
        result = tx_svc.delete_transaction(
            request.user.appprofile.user_id,
            tx_id,
        )
        serializer = TransactionGetSerializer(result['deleted'])
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_transactions_calendar",
        summary="Retrieve calendar aggregates",
        description="Return daily, weekly, and monthly amount aggregates plus day-drill rows for start_date.",
        parameters=[
            OpenApiParameter(name='start_date', type=OpenApiTypes.DATE, required=True, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=OpenApiTypes.DATE, required=True, description='End date (YYYY-MM-DD)'),
        ],
        responses={status.HTTP_200_OK: TransactionCalendarReturnSerializer},
        tags=["Transactions"],
    )
)
class TransactionCalendarView(APIView):
    serializer_class = TransactionCalendarReturnSerializer

    @staticmethod
    def _parse_date_or_400(raw: str | None, field_name: str) -> date:
        if not raw:
            raise ValidationError({field_name: "This query parameter is required."})
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError({field_name: "Use YYYY-MM-DD format."}) from exc

    def get(self, request):
        uid = request.user.appprofile.user_id
        start_date = self._parse_date_or_400(request.query_params.get("start_date"), "start_date")
        end_date = self._parse_date_or_400(request.query_params.get("end_date"), "end_date")
        if end_date < start_date:
            raise ValidationError({"end_date": "Must be on or after start_date."})
        result = tx_svc.get_transaction_calendar(uid, start_date=start_date, end_date=end_date)
        serializer = TransactionCalendarReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_transactions_visualization",
        summary="Retrieve visualization aggregate packets",
        description=(
            "Return chart-ready transaction and upcoming-expense aggregates for the date range."
        ),
        parameters=[
            OpenApiParameter(name='start_date', type=OpenApiTypes.DATE, required=True, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=OpenApiTypes.DATE, required=True, description='End date (YYYY-MM-DD)'),
        ],
        responses={status.HTTP_200_OK: TransactionVisualizationReturnSerializer},
        tags=["Transactions"],
    )
)
class TransactionVisualizationView(APIView):
    serializer_class = TransactionVisualizationReturnSerializer

    @staticmethod
    def _parse_date_or_400(raw: str | None, field_name: str) -> date:
        if not raw:
            raise ValidationError({field_name: "This query parameter is required."})
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError({field_name: "Use YYYY-MM-DD format."}) from exc

    def get(self, request):
        uid = request.user.appprofile.user_id
        start_date = self._parse_date_or_400(request.query_params.get("start_date"), "start_date")
        end_date = self._parse_date_or_400(request.query_params.get("end_date"), "end_date")
        if end_date < start_date:
            raise ValidationError({"end_date": "Must be on or after start_date."})
        result = tx_svc.get_transaction_visualization(uid, start_date=start_date, end_date=end_date)
        serializer = TransactionVisualizationReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

