"""Stable payment-source linkage helpers (source_id mirrors tx_id pattern)."""

from __future__ import annotations

import uuid
from datetime import date

from finance.models import PaymentSource


def generate_source_id(timezone_date: date) -> str:
    """Return a stable source id: ``{date}-{uuid8upper}``."""
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"{timezone_date}-{unique_id}"


def build_source_maps(sources) -> tuple[dict[str, str], dict[str, str]]:
    """Build lowercase name→id and id→display-name maps from PaymentSource rows."""
    name_to_id: dict[str, str] = {}
    id_to_name: dict[str, str] = {}
    for src in sources:
        name_to_id[str(src.source).lower()] = src.source_id
        id_to_name[src.source_id] = src.source
    return name_to_id, id_to_name


def resolve_name_to_id(name: str | None, maps: tuple[dict[str, str], dict[str, str]]) -> str | None:
    """Resolve a display name (case-insensitive) to source_id."""
    if name is None or name == "":
        return None
    name_to_id, _ = maps
    return name_to_id.get(str(name).lower())


def resolve_id_to_name(source_id: str | None, maps: tuple[dict[str, str], dict[str, str]]) -> str | None:
    """Resolve source_id to display name."""
    if source_id is None or source_id == "":
        return None
    _, id_to_name = maps
    return id_to_name.get(source_id)


def names_to_ids(names: list[str], maps: tuple[dict[str, str], dict[str, str]]) -> list[str]:
    """Convert display names to source_ids; unknown names are dropped."""
    name_to_id, _ = maps
    out: list[str] = []
    for name in names:
        sid = name_to_id.get(str(name).lower())
        if sid:
            out.append(sid)
    return out


def ids_to_names(ids: list[str], maps: tuple[dict[str, str], dict[str, str]]) -> list[str]:
    """Convert source_ids to display names; unknown ids are omitted."""
    _, id_to_name = maps
    out: list[str] = []
    for sid in ids:
        name = id_to_name.get(sid)
        if name is not None:
            out.append(name)
    return out


def load_source_maps(uid) -> tuple[dict[str, str], dict[str, str]]:
    """Load name/id maps for a user in one query."""
    sources = list(PaymentSource.objects.for_user(uid))
    return build_source_maps(sources)


def build_source_check(sources) -> set[str]:
    """Accept display names and source_ids for transaction source validation."""
    out: set[str] = set()
    for src in sources:
        out.add(src.source)
        out.add(src.source_id)
    return out


def resolve_transactions_for_api(transactions, maps: tuple[dict[str, str], dict[str, str]]):
    """Replace stored source_id with display name on in-memory transaction rows (API only)."""
    for tx in transactions:
        display = resolve_id_to_name(tx.source, maps)
        if display is not None:
            tx.source = display


def resolve_upcoming_expenses_for_api(expenses, maps: tuple[dict[str, str], dict[str, str]]):
    """Replace stored source_id with display name on in-memory upcoming expense rows (API only)."""
    for expense in expenses:
        if not expense.source:
            continue
        display = resolve_id_to_name(expense.source, maps)
        if display is not None:
            expense.source = display
