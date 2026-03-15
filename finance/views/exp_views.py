from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes

# Service Imports
import finance.services.expense_services as exp_svc

# Serializer Imports
from api_tools.serializers.exp_serializers import(
    ExpenseSerializer,
    ExpenseSetSerializer,
    ExpenseSetReturnSerializer,
    ExpenseGetReturnSerializer
)
from api_tools.serializers.spectactular_serializers import SpectacularExpenseSerializer

@extend_schema_view(    
    post=extend_schema(
        summary="Add an expense",
        description="Adds a planned expense to the user's account.",
        request=ExpenseSerializer,
        responses={status.HTTP_201_CREATED: ExpenseSerializer},
        tags=["Upcoming Expenses"]
    ),
    get=extend_schema(
        summary="Retrieve an expense",
        description="Retrieves a single planned expense for a user.  Accepts optional filters.\n"
                    "If start is set with no end, will return all expenses after start.\n"
                    "If end is set with no start, will return all expenses before end.\n"
                    "If for_month is set, will return expenses for current month.",
        parameters=[
            OpenApiParameter(name='name', type=OpenApiTypes.STR, description='Filter by expense name'),
            OpenApiParameter(name='due_date', type=OpenApiTypes.STR, description='Filter by due date'),
            OpenApiParameter(name='paid_flag', type=OpenApiTypes.BOOL, description='Filter by paid flag'),
            OpenApiParameter(name='recurring', type=OpenApiTypes.BOOL, description='Filter by recurring flag'),
            OpenApiParameter(name='start_date', type=OpenApiTypes.STR, description='Filter by expense start date'),
            OpenApiParameter(name='end_date', type=OpenApiTypes.STR, description='Filter by expense end date'),
            OpenApiParameter(name='start', type=OpenApiTypes.STR, description='Filter for a start date'),
            OpenApiParameter(name='end', type=OpenApiTypes.STR, description='Filter for an end date'),
            OpenApiParameter(name='for_month', type=OpenApiTypes.BOOL, description='Filter by current month'),
            OpenApiParameter(name='remaining', type=OpenApiTypes.BOOL, description='Filter by remaining'),
            OpenApiParameter(name='upcoming', type=OpenApiTypes.BOOL, description='Filter by upcoming'),
        ],
        responses={status.HTTP_200_OK: SpectacularExpenseSerializer(many=True)},
        tags=["Upcoming Expenses"]
    ),
    patch=extend_schema(
        summary="Not allowed.",
        description="For financial fidelity, this endpoint is not allowed.",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["Upcoming Expenses"]
    ),
    put=extend_schema(
        summary="Update an expense",
        description="Updates an existing expense identified by its name.",
        request=ExpenseSerializer,
        responses={status.HTTP_200_OK: ExpenseSerializer(many=True)},
        tags=["Upcoming Expenses"]
    ),
    delete=extend_schema(
        summary="Delete an expense",
        description="Deletes an existing expense identified by its name.",
        responses={status.HTTP_200_OK: ExpenseSerializer(many=True)},
        tags=["Upcoming Expenses"]
    )
)
class UpcomingExpenseView(APIView):
    def post(self, request):
        is_many = isinstance(request.data, list)
        serializer = ExpenseSetSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        if is_many:
            result = exp_svc.bulk_add_expenses(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        else:
            result = exp_svc.add_expense(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        serializer = ExpenseSetReturnSerializer(result['added'], many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request, name: str = None):
        uid = request.user.appprofile.user
        if name:
            result = exp_svc.get_expense(uid=uid, name=request.query_params['name'])
            serializer = ExpenseSerializer(result['expense'])
            return Response({'expenses': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)
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
        result = exp_svc.get_expenses(uid=uid, **filter_params)
        serializer = ExpenseGetReturnSerializer(result['expenses'], many=True)
        return Response({'expenses': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)

    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def patch(self, request):
        result = exp_svc.update_expense(
            uid=request.user.appprofile.user,
            expense_name=request.data['name'],
            data=request.data
        )
        serializer = ExpenseSetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        result = exp_svc.delete_expense(
            uid=request.user.appprofile.user,
            expense_name=request.data['name']
        )
        serializer = ExpenseSetReturnSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
