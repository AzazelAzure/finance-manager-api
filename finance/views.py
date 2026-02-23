"""
This module defines all views for the finance manager application.

Attributes:
    TransactionView: View for transactions.
    AssetView: View for assets.
    SourceView: View for sources.
    UpcomingExpenseView: View for upcoming expenses.
    TagView: View for tags.
    AppProfileView: View for app profiles.
    UserView: View for users.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
import finance.services.transaction_services as tx_svc
import finance.services.source_services as src_svc
import finance.services.expense_services as exp_svc
import finance.services.asset_services as asset_svc
import finance.services.tag_services as tag_svc
import finance.services.user_services as user_svc
from .api_tools.serializers import (
    ExpenseSerializer,
    SourceSerializer,
    AssetSerializer,
    TransactionSerializer,
    TagSerializer,
    AppProfileSerializer,
    UserSerializer,
    SnapshotSerializer,
    SpectacularTxSerializer,
    SpectacularExpenseSerializer
)

# TODO: Add documentation
# TODO: Add logging

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
        ],
        responses={status.HTTP_200_OK: SpectacularTxSerializer},
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
        serializer = TransactionSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Handle Transactions based of list or single
        if is_many:
            for item in serializer.data:
                if item.get('tags'):
                    # Check if tags is a list, if not, make it a list
                    if not isinstance(item['tags'], list):
                        item['tags'] = [item['tags']]
                if item.get('tx_id') or item.get('entry_id'):
                    return Response(status=status.HTTP_403_FORBIDDEN)
            result = tx_svc.add_bulk_transactions(
                data=serializer.data,
                uid=request.user.appprofile.user_id)
        else:
            if serializer.data.get('tags'):
                # Check if tags is a list, if not, make it a list
                if not isinstance(serializer.data['tags'], list):
                    serializer.data['tags'] = [serializer.data['tags']]
            if serializer.data.get('tx_id') or serializer.data.get('entry_id'):
                return Response(status=status.HTTP_403_FORBIDDEN)
            result = tx_svc.add_transaction(
                data=serializer.data,
                uid=request.user.appprofile.user_id)
            
        # Serialize and return
        serializer = TransactionSerializer(result['added'], many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, tx_id: str = None):
        uid = request.user.appprofile.user_id
        
        if tx_id: # If tx_id is provided in the URL path, get a single transaction
            result = tx_svc.user_get_transaction(uid=uid, tx_id=tx_id)
            serializer = TransactionSerializer(result['transaction'])
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
        }
        
        # Remove None values to avoid passing none to the service function if not provided
        filter_params = {k: v for k, v in filter_params.items() if v is not None}
        # If no filters are provided, returns all transactions
        result = tx_svc.user_get_transactions(uid=uid, **filter_params)
        serializer = TransactionSerializer(result['transactions'], many=True)
        return Response({'transactions': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)
    
    def patch(self, request, tx_id: str):
        # Reject attempts to modify tx_id or entry_id
        if request.data.get('tx_id') or request.data.get('entry_id'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # Ensure date is provided
        if not request.date.get('date'):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Check if tags is a list, if not, make it a list
        if not isinstance(request.data['tags'], list):
            request.data['tags'] = [request.data['tags']]

        # Update transaction
        result = tx_svc.user_update_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id,
            data=request.data)
        
        # Serialize and return
        serializer = TransactionSerializer(result['updated'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def delete(self, request, tx_id: str):
        # Delete transaction
        result = tx_svc.user_delete_transaction(
            uid=request.user.appprofile.user_id,
            tx_id=tx_id)
        
        # Serialize and return
        serializer = TransactionSerializer(data=result['deleted'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Asset View
@extend_schema_view(
    post=extend_schema(
        summary="Not allowed.",
        description="All assets are generated automatically.  This endpoint is not allowed.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["Assets"]
    ),
    get=extend_schema(
        summary="Retrieve all assets",
        description="Retrieves either a single asset by source or a list of all assets.",
        responses={status.HTTP_200_OK: AssetSerializer(many=True)},
        tags=["Assets"]
    ),
    patch=extend_schema(
        summary='Update and asset source',
        description="Updates an existing asset identified by its source. Source passed in must exist in PaymentSources, or will raise Validation error.\n"
                    "Forbidden for 'amount' as it is auto calculated based on other fields."
                    "Forbidden to set source to 'unknown' as that is a default empty source.",
        responses = {
            status.HTTP_200_OK: AssetSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None
        },
        tags=["Assets"]
    ),
    put=extend_schema(
        summary="Not allowed.",
        description="For financial fidelity, this endpoint is not allowed.",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["Assets"]
    ),
    delete=extend_schema(
        summary="Not allowed.",
        description="All assets are generated automatically.  This endpoint is not allowed.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["Assets"]
    )
)
class AssetView(APIView):
    """
    View for assets. Directly linked to PaymentSources.\n
    Disallows put methods for financial fidelity.\n
    Disallows post methods due to automatic asset generation.\n
    Disallows delete methods due to automatic asset generation.\n

    Attributes:
        post: Not allowed.
        get: Retrieve either a single asset by source or all assets for user.
        put: Not allowed.
        patch: Update an asset.
        delete: Not allowed.
    """
    def post(self, request):
        """Not allowed."""
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def get(self, request, source=None):
        """
        Retrieve either a single asset by source or all assets for user.
        If source is provided, return a single asset.
        If no source is provided, return all assets for user.

        :param request: HTTP request.
        :param source: Optional source to filter by.
        :return: Serialized asset or serialized set of all assets.
        """
        # Check if source provided, otherwise return all assets
        if not source:
            result = asset_svc.get_all_assets(uid=request.user.appprofile.user_id)
            serializer = AssetSerializer(result['asset'], many=True)
        else:
            result = asset_svc.get_asset(uid=request.user.appprofile.user_id, source=source)
            serializer = AssetSerializer(result['assets'], many=True)
        
        # Return serialized asset or all assets
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, source: str):
        # Catch if source is 'unknown' and return error
        source = source.lower()
        if source == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # Reject attempts to modify amount
        if request.data.get('amount'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        result = asset_svc.update_asset_source(
            uid=request.user.appprofile.user_id,
            data=request.data,
            source=source
        )
        serializer = AssetSerializer(result['updated'])
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, source: str):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def delete(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)


# Source View
@extend_schema_view(
    post=extend_schema(
        summary="Add a payment source",
        description="Adds a payment source to the user's account.\n"
                    "Allows for multiple sources to be created at once.\n"
                    "Forbidden to add 'unknown' source as that is a default empty source.\n"
                    "If forbidden, will return HTTP 400 Bad Request during creation and not add any sources.",
        request=SourceSerializer,
        responses={status.HTTP_201_CREATED: SourceSerializer},
        tags=["Sources"]
    ),
    get=extend_schema(
        summary="Retrieve sources",
        description="Retrieves a list of payment sources for a user.  Accepts optional filters.",
        parameters=[
            OpenApiParameter(name='acc_type', type=OpenApiTypes.STR, description='Filter by account type (e.g., CASH, INVESTMENT, SAVINGS)'),
            OpenApiParameter(name='source', type=OpenApiTypes.STR, description='Filter by source (e.g., VISA, MASTERCARD, AMEX)'),
        ],
        responses={status.HTTP_200_OK: SourceSerializer(many=True)},
        tags=["Sources"]
    ),
    patch=extend_schema(
        summary="Not allowed.",
        description="For financial fidelity, this endpoint is not allowed.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["Sources"]
    ),
    put=extend_schema(
        summary="Update a payment source",
        description="Updates an existing payment source identified by its source.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.",
        request=SourceSerializer,
        responses={
            status.HTTP_200_OK: SourceSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    ),
    delete=extend_schema(
        summary="Delete a payment source",
        description="Deletes an existing payment source identified by its source.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.",
        responses={
            status.HTTP_200_OK: SourceSerializer(many=True),
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["Sources"]
    )
)
class SourceView(APIView):
    """
    View for payment sources.\n
    Disallows patch methods for financial fidelity.

    Attributes:
        post: Add a payment source.
        get: Retrieve sources.
        patch: Not allowed.
        put: Update a payment source.
        delete: Delete a payment source.
    """
    def post(self, request):
        # Check if single or list of sources and serialize
        is_many = isinstance(request.data, list)
        serializer = SourceSerializer(request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Handle Sources based of list or single
        if is_many:
            result = src_svc.bulk_add_sources(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        else:
            result = src_svc.add_source(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        
        # Serialize and return
        serializer = SourceSerializer(result['added'], many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def patch(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    def get(self, request):
        # Get sources, filter by params, serialize, return
        result = src_svc.get_sources(uid=request.user.appprofile.user, **request.query_params)
        serializer = SourceSerializer(result['sources'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, src: str):
        if src == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.update_source(
            uid=request.user.appprofile.user,
            source=src,
            data=request.data
        )
        serializer = SourceSerializer(result['updated'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        if request.data['source'] == "unknown":
            return Response(status=status.HTTP_403_FORBIDDEN)
        result = src_svc.delete_source(
            uid=request.user.appprofile.user,
            source=request.data['source']
        )
        serializer = SourceSerializer(result['deleted'], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

# Upcoming Expense View
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
        serializer = ExpenseSerializer(data=request.data, many=is_many)
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
        serializer = ExpenseSerializer(result['added'], many=True)
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
        serializer = ExpenseSerializer(result['expenses'], many=True)
        return Response({'expenses': serializer.data, 'amount': result['amount']}, status=status.HTTP_200_OK)

    def patch(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def put(self, request):
        result = exp_svc.update_expense(
            uid=request.user.appprofile.user,
            expense_name=request.data['name'],
            data=request.data
        )
        serializer = ExpenseSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        result = exp_svc.delete_expense(
            uid=request.user.appprofile.user,
            expense_name=request.data['name']
        )
        serializer = ExpenseSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Tag View
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
        # Check if single or list of tags and serialize
        is_many = isinstance(request.data, list)
        serializer = TagSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Handle Tags based of list or single
        if is_many:
            result = tag_svc.bulk_add_tags(
                uid=request.user.appprofile.user,
                data=serializer.data
            )
        else:
            result = tag_svc.add_tag(
                uid=request.user.appprofile.user,
                data=serializer.data
            )

        # Serialize and return
        serializer = TagSerializer(result['added'],many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        # Get tags, serialize, return
        result = tag_svc.get_tags(uid=request.user.appprofile.user)
        serializer = TagSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    def put(self, request, name: str):
        # Change name of tag, serialize, return
        result = tag_svc.update_tag(
            uid=request.user.appprofile.user,
            name=name,
            data=request.data
        )
        serializer = TagSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    
    def delete(self, request):
        # Delete tag, serialize, return
        result = tag_svc.delete_tag(
            uid=request.user.appprofile.user,
            tag_name=request.data['name']
        )
        serializer = TagSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# AppProfile View
@extend_schema_view(
    post=extend_schema(
        summary="Not allowed.",
        description="All app profiles are generated automatically.  This endpoint is not allowed. Automatically generated on user creation.",
        responses={status.HTTP_403_FORBIDDEN: None},
        tags=["App Profiles"]
    ),
    get=extend_schema(
        summary="Retrieve app profile",
        description="Retrieves the spend accounts and base currency for a user.",
        responses={status.HTTP_200_OK: AppProfileSerializer(many=True)},
        tags=["App Profiles"]
    ),
    patch=extend_schema(
        summary="Update app profile",
        description="Updates the spend accounts and base currency for a user.\n"
                    "Forbidden for 'unknown' source as that is a default empty source.  This cannot be used as spend account.",
        request=AppProfileSerializer,
        responses={
            status.HTTP_200_OK: AppProfileSerializer,
            status.HTTP_403_FORBIDDEN: None,
            },
        tags=["App Profiles"]
    ),
    put=extend_schema(
        summary="Not allowed.",
        description="Not allowed as only fields that can be updated for user are spend accounts and base currency.\n",
        responses={status.HTTP_405_METHOD_NOT_ALLOWED: None},
        tags=["App Profiles"]
    ),
    delete=extend_schema(
        summary="Not allowed.",
        description="All app profiles are generated automatically.  This endpoint is not allowed. To delete, delete the user account.",
        responses={status.HTTP_501_NOT_IMPLEMENTED: None},
        tags=["App Profiles"]
    )
)
class AppProfileView(APIView):
    """
    App profile view.

    Attributes:
        post: Not allowed.
        get: Retrieve app profile.
        patch: Update app profile.
        put: Not allowed
        delete: Not allowed.
    """
    def post(self, request):
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def get(self, request, snapshot: bool = False):
        uid = request.user.appprofile.user_id
        # Return the snapshot if requested, otherwise return the app profile
        if snapshot:
            result = user_svc.user_get_totals(uid=uid)
            serializer = SnapshotSerializer(result, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Return the app profile.  Only returns spend account and base currency.
        result = user_svc.user_get_info(uid=uid)
        serializer = AppProfileSerializer(result, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, base_currency: str=None, spend_accounts: list=None):
        uid = request.user.appprofile.user_id
        if base_currency:
            result = user_svc.user_update_base_currency(uid=uid, data={'code': base_currency})
            serializer = AppProfileSerializer(result)
            return Response(serializer.data, status=status.HTTP_200_OK)
        if spend_accounts:
            for item in spend_accounts:
                item = item.lower()
            if "unknown" in spend_accounts:
                return Response(status=status.HTTP_403_FORBIDDEN)
            result = user_svc.user_update_spend_accounts(uid=uid, data=spend_accounts)
            serializer = AppProfileSerializer(data=result)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def delete(self, request):
        return Response(status=status.HTTP_501_NOT_IMPLEMENTED)


# User View
@extend_schema_view(
    post=extend_schema(
        summary="Create one or more users",
        description="Allows creation of a single user or a list of users.",
        request=UserSerializer,
        responses={status.HTTP_201_CREATED: OpenApiTypes.OBJECT}, 
        tags=["Users"]
    ),
    get=extend_schema(
        summary="Retrieves users email.",
        description="Retrieves the email for the currently logged in user.",
        responses={status.HTTP_200_OK: OpenApiTypes.OBJECT},
        tags=["Users"]
    ),
    patch=extend_schema(
        summary="Update a user",
        description="Updates an existing user identified by its username and password.  Used to update password.",
        request=UserSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    ),
    delete=extend_schema(
        summary="Delete a user",
        description="Deletes an existing user identified by its username.",
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_403_FORBIDDEN: OpenApiTypes.OBJECT,
            },
        tags=["Users"]
    )
)
class UserView(APIView):
    def post(self, request):
        # Get user model
        User = get_user_model()

        # Check if all user credentials provided
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create user
        user = User.objects.create_user(
            username=serializer.data['username'],
            email=serializer.data['user_email'],
            password=serializer.data['password']
        )
        return Response({'message': "User created successfully"}, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        serialzer = UserSerializer(data=request.user)
        serialzer.is_valid(raise_exception=True)
        return Response({'email': request.user.email}, status=status.HTTP_200_OK)

    def patch(self, request):
        User = get_user_model()
        if request.data['username'] != request.user.username:
            return Response({'message': "Incorrect user."}, status=status.HTTP_403_FORBIDDEN)
        user = User.objects.get(username=request.data['username'])
        user.set_password(request.data['password'])
        user.save()
        return Response({'message': "Password updated successfully"}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        User = get_user_model()
        if request.data['username'] != request.user.username:
            return Response({'message': "Incorrect user."}, status=status.HTTP_403_FORBIDDEN)
        user = User.objects.get(username=request.data['username'])
        user.delete()
        return Response({'message': "User deleted successfully"}, status=status.HTTP_200_OK)