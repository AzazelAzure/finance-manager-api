from datetime import date
from decimal import ROUND_UP, Decimal, InvalidOperation

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import SavingsGoal
from finance.logic.source_linkage import load_source_maps, resolve_id_to_name, resolve_name_to_id

CYCLES_PER_YEAR = {
    "weekly": 52,
    "biweekly": 26,
    "semimonthly": 24,
    "monthly": 12,
}


def compute_per_cycle_required(goal, profile) -> Decimal:
    remaining = max(goal.target_amount - goal.current_amount, Decimal("0"))
    if remaining == 0:
        return Decimal("0")
    today = date.today()
    days_remaining = (goal.target_date - today).days
    if days_remaining <= 0:
        return remaining
    freq = profile.pay_cycle_frequency or "monthly"
    days_per_cycle = round(365 / CYCLES_PER_YEAR.get(freq, 12))
    periods = max(days_remaining // days_per_cycle, 1)
    # Round up so a positive remaining never reports 0.00 per cycle (under-saving guidance).
    return (remaining / periods).quantize(Decimal("0.01"), rounding=ROUND_UP)


def _goal_payload(goal, profile) -> dict:
    maps = load_source_maps(str(profile.user_id))
    source_name = resolve_id_to_name(goal.source, maps) if goal.source else None
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": str(goal.target_amount),
        "current_amount": str(goal.current_amount),
        "currency": goal.currency,
        "target_date": goal.target_date.isoformat(),
        "source": source_name,
        "per_cycle_required": str(compute_per_cycle_required(goal, profile)),
    }


def _parse_decimal(value, field_name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field_name} must be a finite number")
    if parsed < 0:
        raise ValueError(f"{field_name} must not be negative")
    return parsed


def _parse_name(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("name must be a non-empty string")
    return value.strip()


def _parse_date(value, field_name: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid ISO date") from exc


def _resolve_source_id(profile, source_name):
    if source_name is None:
        return None
    uid = str(profile.user_id)
    maps = load_source_maps(uid)
    source_id = resolve_name_to_id(str(source_name).lower(), maps)
    if not source_id:
        raise ValueError("source not found for this user")
    return source_id


class SavingsGoalListCreateView(APIView):
    def get(self, request):
        profile = request.user.appprofile
        goals = SavingsGoal.objects.filter(uid=profile)
        return Response(
            [_goal_payload(goal, profile) for goal in goals],
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        profile = request.user.appprofile
        data = request.data
        missing = [field for field in ("name", "target_amount", "target_date") if field not in data]
        if missing:
            return Response(
                {"detail": f"Missing required field(s): {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            name = _parse_name(data["name"])
            target_amount = _parse_decimal(data["target_amount"], "target_amount")
            target_date = _parse_date(data["target_date"], "target_date")
            current_amount = _parse_decimal(data.get("current_amount", "0"), "current_amount")
            source = _resolve_source_id(profile, data.get("source")) if "source" in data else None
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        currency = data.get("currency") or profile.base_currency
        goal = SavingsGoal.objects.create(
            uid=profile,
            name=name,
            target_amount=target_amount,
            currency=currency,
            target_date=target_date,
            current_amount=current_amount,
            source=source,
        )
        return Response(_goal_payload(goal, profile), status=status.HTTP_201_CREATED)


class SavingsGoalDetailView(APIView):
    def _get_goal(self, profile, pk):
        try:
            return SavingsGoal.objects.get(pk=pk, uid=profile)
        except SavingsGoal.DoesNotExist:
            return None

    def get(self, request, pk: int):
        profile = request.user.appprofile
        goal = self._get_goal(profile, pk)
        if goal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(_goal_payload(goal, profile), status=status.HTTP_200_OK)

    def patch(self, request, pk: int):
        profile = request.user.appprofile
        goal = self._get_goal(profile, pk)
        if goal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        data = request.data
        updatable = {"name", "target_amount", "target_date", "current_amount", "source"}
        if not any(field in data for field in updatable):
            return Response(
                {"detail": "No updatable fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if "name" in data:
                goal.name = _parse_name(data["name"])
            if "target_amount" in data:
                goal.target_amount = _parse_decimal(data["target_amount"], "target_amount")
            if "target_date" in data:
                goal.target_date = _parse_date(data["target_date"], "target_date")
            if "current_amount" in data:
                goal.current_amount = _parse_decimal(data["current_amount"], "current_amount")
            if "source" in data:
                goal.source = _resolve_source_id(profile, data["source"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        goal.save()
        return Response(_goal_payload(goal, profile), status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        profile = request.user.appprofile
        goal = self._get_goal(profile, pk)
        if goal is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        goal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
