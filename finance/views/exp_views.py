from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

# Service Imports
import finance.services.expense_services as exp_svc

# Serializer Imports
from finance.api_tools.serializers.exp_serializers import(
    ExpenseSerializer,
    ExpensePostSerializer,
    ExpensePutSerializer,
    ExpensePatchSerializer,
    ExpenseSetReturnSerializer,
    ExpenseCatchUpSerializer,
)
from finance.api_tools.serializers.spectactular_serializers import SpectacularExpenseSerializer
from finance.models import UpcomingExpense

@extend_schema_view(    
    post=extend_schema(
        operation_id="finance_upcoming_expenses_create",
        summary="Add an expense",
        description="Create one expense object or a list of expense objects.",
        request=ExpensePostSerializer,
        responses={status.HTTP_201_CREATED: ExpenseSetReturnSerializer},
        tags=["Upcoming Expenses"]
    ),
    get=extend_schema(
        operation_id="finance_upcoming_expenses_list",
        summary="Retrieve expenses list",
        description="Retrieve expenses with optional filters.\n"
                    "Aggregate totals are included in the response payload.",
        parameters=[
            OpenApiParameter(name='name', type=OpenApiTypes.STR, description='Filter by expense name'),
            OpenApiParameter(name='due_date', type=OpenApiTypes.STR, description='Filter by due date'),
            OpenApiParameter(name='paid_flag', type=OpenApiTypes.BOOL, description='Filter by paid flag'),
            OpenApiParameter(name='recurring', type=OpenApiTypes.BOOL, description='Filter by recurring flag'),
            OpenApiParameter(name='start_date', type=OpenApiTypes.STR, description='Filter by expense start date'),
            OpenApiParameter(name='end_date', type=OpenApiTypes.STR, description='Filter by expense end date'),
            OpenApiParameter(name='start', type=OpenApiTypes.STR, description='Filter for a start date'),
            OpenApiParameter(name='end', type=OpenApiTypes.STR, description='Filter for an end date'),
            OpenApiParameter(name='for_month', type=OpenApiTypes.STR, description='Filter by month in YYYY-MM format'),
            OpenApiParameter(name='remaining', type=OpenApiTypes.BOOL, description='Filter by remaining'),
            OpenApiParameter(name='upcoming', type=OpenApiTypes.BOOL, description='Filter by upcoming'),
        ],
        responses={status.HTTP_200_OK: SpectacularExpenseSerializer(many=True)},
        tags=["Upcoming Expenses"]
    )
)
class UpcomingExpenseListCreateView(APIView):
    serializer_class = ExpensePostSerializer

    def post(self, request):
        is_many = isinstance(request.data, list)
        serializer = ExpensePostSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        result = exp_svc.add_expense(
            request.user.appprofile.user_id,
            serializer.data,
        )
        serializer = ExpenseSetReturnSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        uid = request.user.appprofile.user_id
        filter_params = {
            'remaining': request.query_params.get('remaining'),
            'recurring': request.query_params.get('recurring'),
            'paid_flag': request.query_params.get('paid_flag'),
            'for_month': request.query_params.get('for_month'),
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'due_date': request.query_params.get('due_date'),
            'upcoming': request.query_params.get('upcoming'),
            'start': request.query_params.get('start'),
            'end': request.query_params.get('end'),
        }
        filter_params = {k: v for k, v in filter_params.items() if v is not None}
        result = exp_svc.get_expenses(uid, **filter_params)
        serializer = ExpenseSerializer(result['expenses'], many=True)
        return Response({'expenses': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        operation_id="finance_upcoming_expenses_retrieve",
        summary="Retrieve an expense",
        description="Retrieve a single expense identified by name.",
        responses={status.HTTP_200_OK: ExpenseSerializer},
        tags=["Upcoming Expenses"]
    ),
    patch=extend_schema(
        operation_id="finance_upcoming_expenses_partial_update",
        summary="Partially update an expense",
        description="Partially update an existing expense identified by name.",
        request=ExpensePatchSerializer,
        responses={status.HTTP_200_OK: ExpenseSetReturnSerializer},
        tags=["Upcoming Expenses"]
    ),
    put=extend_schema(
        operation_id="finance_upcoming_expenses_update",
        summary="Update an expense",
        description="Replace mutable fields for an existing expense identified by name.",
        request=ExpensePutSerializer,
        responses={status.HTTP_200_OK: ExpenseSetReturnSerializer},
        tags=["Upcoming Expenses"]
    ),
    delete=extend_schema(
        operation_id="finance_upcoming_expenses_destroy",
        summary="Delete an expense",
        description="Deletes an existing expense identified by its name.",
        responses={status.HTTP_200_OK: ExpenseSetReturnSerializer},
        tags=["Upcoming Expenses"]
    )
)
class UpcomingExpenseDetailView(APIView):
    serializer_class = ExpensePutSerializer

    def get(self, request, name: str):
        uid = request.user.appprofile.user_id
        result = exp_svc.get_expense(uid, name)
        serializer = ExpenseSerializer(result['expense'])
        return Response({'expense': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)

    def put(self, request, name: str):
        uid = request.user.appprofile.user_id
        existing = UpcomingExpense.objects.for_user(uid).filter(name__iexact=str(name).strip()).first()
        serializer = ExpensePutSerializer(
            data=request.data,
            context={"existing": existing},
        )
        serializer.is_valid(raise_exception=True)
        result = exp_svc.update_expense(
            request.user.appprofile.user_id,
            name,
            serializer.data,
        )
        return Response(ExpenseSetReturnSerializer(result).data, status=status.HTTP_200_OK)
    
    def patch(self, request, name: str):
        uid = request.user.appprofile.user_id
        existing = UpcomingExpense.objects.for_user(uid).filter(name__iexact=str(name).strip()).first()
        serializer = ExpensePatchSerializer(
            data=request.data,
            partial=True,
            context={"existing": existing},
        )
        serializer.is_valid(raise_exception=True)
        result = exp_svc.update_expense(
            request.user.appprofile.user_id,
            name,
            serializer.data,
        )
        return Response(ExpenseSetReturnSerializer(result).data, status=status.HTTP_200_OK)
    
    def delete(self, request, name: str):
        result = exp_svc.delete_expense(
            request.user.appprofile.user_id,
            name,
        )
        return Response(ExpenseSetReturnSerializer(result).data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        operation_id="finance_upcoming_expenses_catch_up",
        summary="Catch up an overdue bill",
        description=(
            "Advance an overdue upcoming expense by its bill interval. "
            "Omit ``periods`` to catch up all missed periods (max 24). "
            "Pass ``periods: 1`` for a single mark-paid-and-advance step."
        ),
        request=ExpenseCatchUpSerializer,
        responses={status.HTTP_200_OK: ExpenseSetReturnSerializer},
        tags=["Upcoming Expenses"],
    )
)
class UpcomingExpenseCatchUpView(APIView):
    serializer_class = ExpenseCatchUpSerializer

    def post(self, request, name: str):
        serializer = ExpenseCatchUpSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        periods = serializer.validated_data.get("periods")
        result = exp_svc.catch_up_expense(
            request.user.appprofile.user_id,
            name,
            periods=periods,
        )
        return Response(ExpenseSetReturnSerializer(result).data, status=status.HTTP_200_OK)
