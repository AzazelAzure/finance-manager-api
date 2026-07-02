from rest_framework import serializers
from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer

class TransactionSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=200
        )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    source = serializers.CharField(max_length=50)
    currency = serializers.CharField(max_length=3)
    tags = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    tx_type = serializers.CharField(max_length=10)
    category = serializers.CharField(max_length=200, required=False)
    auto_deducted = serializers.BooleanField(required=False, default=False)

class TransactionSetSerializer(TransactionSerializer):
    bill = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)

class TransactionAcceptedSerializer(TransactionSetSerializer):
    tx_id = serializers.CharField(max_length=20)
    created_on = serializers.DateField()

class TransactionSetReturnSerializer(serializers.Serializer):
    rejected = TransactionSetSerializer(many=True, required=False)
    accepted = TransactionAcceptedSerializer(many=True, required=False)
    updated = TransactionAcceptedSerializer(many=True, required=False)
    snapshot = FinancialSnapshotSerializer(required=False)

class TransactionGetSerializer(TransactionSerializer):
    tx_id = serializers.CharField(max_length=20)
    created_on = serializers.DateField()
    bill = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    snapshot = FinancialSnapshotSerializer(required=False)


class TransactionGetReturnSerializer(serializers.Serializer):
    transactions = TransactionGetSerializer(many=True)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_out = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_transfer_in = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_leaks = serializers.DecimalField(max_digits=10, decimal_places=2)
    expense_by_category = serializers.DictField(child=serializers.DecimalField(max_digits=10, decimal_places=2), required=False)


class CalendarBucketSerializer(serializers.Serializer):
    period = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class CalendarDayAggregateSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tx_count = serializers.IntegerField(min_value=0)
    heat_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    heat_intensity = serializers.IntegerField(min_value=0)


class CalendarDueEventSerializer(serializers.Serializer):
    date = serializers.DateField()
    expense_name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_base = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    paid_flag = serializers.BooleanField()
    is_recurring = serializers.BooleanField()


class TransactionCalendarReturnSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    base_currency = serializers.CharField(max_length=3)
    display_currency_mode = serializers.ChoiceField(choices=["base", "original"])
    heat_metric_mode = serializers.ChoiceField(choices=["net", "expense_only", "count"])
    heat_max = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly = CalendarBucketSerializer(many=True)
    weekly = CalendarBucketSerializer(many=True)
    daily = CalendarDayAggregateSerializer(many=True)
    due_events = CalendarDueEventSerializer(many=True)
    day_drill = TransactionGetSerializer(many=True)


class VisualizationFlowDailySerializer(serializers.Serializer):
    date = serializers.DateField()
    income = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    net = serializers.DecimalField(max_digits=12, decimal_places=2)
    tx_count = serializers.IntegerField(min_value=0)


class VisualizationTypeTotalSerializer(serializers.Serializer):
    tx_type = serializers.CharField(max_length=12)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class VisualizationCategorySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class VisualizationUpcomingExpensePointSerializer(serializers.Serializer):
    due_date = serializers.DateField(allow_null=True)
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    paid_flag = serializers.BooleanField()


class VisualizationUpcomingMonthlySerializer(serializers.Serializer):
    period = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_count = serializers.IntegerField(min_value=0)


class VisualizationUpcomingStatusSerializer(serializers.Serializer):
    paid_count = serializers.IntegerField(min_value=0)
    unpaid_count = serializers.IntegerField(min_value=0)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    unpaid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class TransactionVisualizationReturnSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    flow_daily = VisualizationFlowDailySerializer(many=True)
    tx_type_totals = VisualizationTypeTotalSerializer(many=True)
    top_expense_categories = VisualizationCategorySerializer(many=True)
    upcoming_expenses_timeline = VisualizationUpcomingExpensePointSerializer(many=True)
    upcoming_expenses_monthly = VisualizationUpcomingMonthlySerializer(many=True)
    upcoming_expenses_status = VisualizationUpcomingStatusSerializer()