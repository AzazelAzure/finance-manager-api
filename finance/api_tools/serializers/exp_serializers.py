from rest_framework import serializers

from finance.api_tools.serializers.base_serializers import FinancialSnapshotSerializer
from finance.logic.source_linkage import load_source_maps, resolve_id_to_name
from finance.models import UpcomingExpense

_CADENCE_CHOICES = [choice.value for choice in UpcomingExpense.Cadence]


def _validate_cadence_fields(attrs, existing_cadence="monthly", existing_days=None):
    """Validate cadence/custom_interval_days; mutates attrs to clear days when non-custom."""
    cadence = attrs.get("cadence", existing_cadence)
    if "custom_interval_days" in attrs:
        days = attrs.get("custom_interval_days")
    else:
        days = existing_days
    if cadence == "custom" and not (days and days > 0):
        raise serializers.ValidationError(
            {"custom_interval_days": "Required and must be > 0 when cadence is 'custom'."}
        )
    if cadence != "custom":
        attrs["custom_interval_days"] = None
    return attrs


class ExpenseSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField(required=False)
    currency = serializers.CharField(max_length=3, required=False)
    is_recurring = serializers.BooleanField(required=False)
    bill_class = serializers.ChoiceField(choices=["rigid", "volatile"], required=False)
    planned_partial_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    cycle_residual_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    remainder_due_date = serializers.DateField(required=False, allow_null=True)
    cadence = serializers.ChoiceField(choices=_CADENCE_CHOICES, required=False)
    custom_interval_days = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    auto_deduct = serializers.BooleanField(required=False, default=False)
    source = serializers.CharField(max_length=50, required=False, allow_null=True)

    def validate(self, attrs):
        existing = self.context.get("existing")
        existing_cadence = getattr(existing, "cadence", "monthly") if existing else "monthly"
        existing_days = getattr(existing, "custom_interval_days", None) if existing else None
        return _validate_cadence_fields(attrs, existing_cadence, existing_days)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        uid = getattr(instance, "uid", None)
        if uid and getattr(instance, "source", None):
            maps = load_source_maps(uid)
            ret["source"] = resolve_id_to_name(instance.source, maps)
        else:
            ret.setdefault("source", None)
        ret.setdefault("auto_deduct", getattr(instance, "auto_deduct", False))
        return ret


class ExpensePostSerializer(ExpenseSerializer):
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)


class ExpensePutSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField(allow_null=True)
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    paid_flag = serializers.BooleanField()
    currency = serializers.CharField(max_length=3)
    is_recurring = serializers.BooleanField()
    bill_class = serializers.ChoiceField(choices=["rigid", "volatile"], required=False)
    planned_partial_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    cycle_residual_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    remainder_due_date = serializers.DateField(required=False, allow_null=True)
    cadence = serializers.ChoiceField(choices=_CADENCE_CHOICES, required=False)
    custom_interval_days = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    auto_deduct = serializers.BooleanField(required=False, default=False)
    source = serializers.CharField(max_length=50, required=False, allow_null=True)

    def validate(self, attrs):
        existing = self.context.get("existing")
        existing_cadence = getattr(existing, "cadence", "monthly") if existing else "monthly"
        existing_days = getattr(existing, "custom_interval_days", None) if existing else None
        return _validate_cadence_fields(attrs, existing_cadence, existing_days)


class ExpensePatchSerializer(ExpenseSerializer):
    # Compatibility alias for clients that send `paid` in partial updates.
    paid = serializers.BooleanField(required=False, write_only=True)
    # Compatibility alias for clients that send `recurring_flag`.
    recurring_flag = serializers.BooleanField(required=False, write_only=True)

    def validate(self, attrs):
        paid_alias = attrs.pop("paid", None)
        if paid_alias is not None:
            attrs["paid_flag"] = paid_alias
        recurring_alias = attrs.pop("recurring_flag", None)
        if recurring_alias is not None:
            attrs["is_recurring"] = recurring_alias
        return super().validate(attrs)


class ExpenseSetReturnSerializer(ExpenseSerializer):
    rejected = ExpenseSerializer(many=True, required=False)
    accepted = ExpenseSerializer(many=True, required=False)
    updated = ExpenseSerializer(many=True, required=False)
    deleted = ExpenseSerializer(many=True, required=False)
    snapshot = FinancialSnapshotSerializer(required=False)
    periods_advanced = serializers.IntegerField(required=False)
    periods_missed = serializers.IntegerField(required=False)


class ExpenseCatchUpSerializer(serializers.Serializer):
    periods = serializers.IntegerField(required=False, min_value=1, max_value=24)


class ExpenseGetReturnSerializer(serializers.Serializer):
    expenses = ExpenseSerializer(many=True, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
