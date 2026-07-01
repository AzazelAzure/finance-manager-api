"""Day-end balance snapshot computation and persistence (F-001)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import zoneinfo

from finance.logic.convert_currency import convert_currency
from finance.logic.fincalc import Calculator
from finance.logic.source_linkage import load_source_maps, resolve_id_to_name, resolve_name_to_id
from finance.models import AppProfile, BalanceSnapshot, PaymentSource, Transaction


def _quantize(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


def _convert_amount(amount, from_currency: str, to_currency: str) -> Decimal:
    if from_currency == to_currency:
        return _quantize(amount)
    return _quantize(convert_currency(amount, from_currency, to_currency))


def _opening_balances_by_source(uid: str) -> tuple[dict[str, Decimal], dict[str, PaymentSource]]:
    """Return per-source_id opening balance (amount not explained by persisted transactions)."""
    sources = list(PaymentSource.objects.for_user(uid))
    source_map = {source.source_id: source for source in sources}
    openings: dict[str, Decimal] = {}
    for source in sources:
        tx_sum = Decimal("0.00")
        for tx in Transaction.objects.for_user(uid).filter(source=source.source_id):
            tx_sum += _convert_amount(tx.amount, tx.currency, source.currency)
        openings[source.source_id] = _quantize(Decimal(source.amount) - tx_sum)
    return openings, source_map


def closing_balances_as_of(uid: str, as_of_date: date) -> tuple[dict[str, Decimal], dict[str, PaymentSource]]:
    """Compute per-source closing balance through ``as_of_date`` (inclusive)."""
    openings, source_map = _opening_balances_by_source(uid)
    balances = dict(openings)
    txs = (
        Transaction.objects.for_user(uid)
        .filter(date__lte=as_of_date)
        .order_by("date", "tx_id")
    )
    for tx in txs:
        source = source_map.get(tx.source)
        if source is None:
            continue
        balances[tx.source] = balances.get(tx.source, Decimal("0.00")) + _convert_amount(
            tx.amount,
            tx.currency,
            source.currency,
        )
    return balances, source_map


def persist_snapshots_for_date(uid: str, snapshot_date: date) -> int:
    """Upsert day-end rows for every payment source. Returns rows written."""
    balances, source_map = closing_balances_as_of(uid, snapshot_date)
    written = 0
    for source_id, balance in balances.items():
        source = source_map.get(source_id)
        if source is None:
            continue
        BalanceSnapshot.objects.update_or_create(
            uid=uid,
            source=source_id,
            snapshot_date=snapshot_date,
            defaults={
                "closing_balance": _quantize(balance),
                "currency": source.currency,
            },
        )
        written += 1
    return written


def resolve_date_range(
    profile: AppProfile,
    *,
    range_preset: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[date | None, date]:
    """Return inclusive (start, end) for balance-history queries."""
    tz = zoneinfo.ZoneInfo(profile.timezone or "UTC")
    today = datetime.now(tz).date()
    end = end_date or today
    if start_date is not None:
        return start_date, end
    preset = (range_preset or "30d").lower()
    if preset == "7d":
        return today - timedelta(days=6), end
    if preset == "30d":
        return today - timedelta(days=29), end
    if preset == "90d":
        return today - timedelta(days=89), end
    if preset == "all":
        return None, end
    return today - timedelta(days=29), end


def get_balance_history(
    uid: str,
    profile: AppProfile,
    *,
    source: str | None = None,
    range_preset: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Return serialized balance history in the user's base currency."""
    maps = load_source_maps(uid)
    start, end = resolve_date_range(
        profile,
        range_preset=range_preset,
        start_date=start_date,
        end_date=end_date,
    )
    qs = BalanceSnapshot.objects.for_user(uid)
    if start is not None:
        qs = qs.filter(snapshot_date__gte=start)
    qs = qs.filter(snapshot_date__lte=end)
    if source:
        source_id = resolve_name_to_id(source.strip(), maps)
        if source_id:
            qs = qs.filter(source=source_id)

    calculator = Calculator(profile)
    base_currency = calculator.base_currency
    series = []
    for row in qs.order_by("snapshot_date", "source"):
        amount_base = _quantize(
            Decimal(
                calculator._calc_totals(row.currency, base_currency, row.closing_balance),
            ),
        )
        display_source = resolve_id_to_name(row.source, maps) or row.source
        series.append(
            {
                "date": row.snapshot_date.isoformat(),
                "source": display_source,
                "amount": str(amount_base),
                "currency": base_currency,
            },
        )
    return {"series": series, "base_currency": base_currency}
