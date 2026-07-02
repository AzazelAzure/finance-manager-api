"""
Dashboard widget layout catalog and per-device-class defaults (F-006 T01).

PWA offline read path: layout is server-backed; the web client caches the last
successful GET response per device_class in IndexedDB (Dexie) for offline render.
Offline reads are read-only — layout edits require network and follow the standard
offline mutation guard. When online, GET returns the saved layout or the
device-appropriate server default below.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

WIDGET_CATALOG_IDS: frozenset[str] = frozenset(
    {
        "KPIRow",
        "ProfileOverview",
        "SourceBalances",
        "RecentTransactions",
        "UpcomingBillsWidget",
        "GoalsWidget",
        "BalanceHistoryChart",
        "SpendChart",
        "FlowChart",
        "CategoryPie",
        "TagPie",
        "QuickActions",
    }
)

SIZE_TIERS: frozenset[str] = frozenset({"full", "half"})

DEVICE_CLASSES: frozenset[str] = frozenset({"mobile", "desktop"})

LayoutItem = dict[str, Any]


def _item(widget_id: str, size: str = "full", visible: bool = True) -> LayoutItem:
    return {"widget_id": widget_id, "size": size, "visible": visible}


# Desktop default mirrors the current dashboard render order (DashboardPage.tsx).
DESKTOP_DEFAULT_LAYOUT: list[LayoutItem] = [
    _item("QuickActions", "full"),
    _item("KPIRow", "full"),
    _item("GoalsWidget", "full"),
    _item("UpcomingBillsWidget", "full"),
    _item("FlowChart", "half"),
    _item("SpendChart", "half"),
    _item("CategoryPie", "half"),
    _item("TagPie", "half"),
    _item("SourceBalances", "half"),
    _item("BalanceHistoryChart", "half"),
    _item("ProfileOverview", "half"),
    _item("RecentTransactions", "full"),
]

# Mobile default is STS-first: survival KPIs and upcoming obligations before analytics.
MOBILE_DEFAULT_LAYOUT: list[LayoutItem] = [
    _item("KPIRow", "full"),
    _item("UpcomingBillsWidget", "full"),
    _item("QuickActions", "full"),
    _item("SourceBalances", "full"),
    _item("RecentTransactions", "full"),
    _item("GoalsWidget", "full"),
    _item("ProfileOverview", "full"),
    _item("BalanceHistoryChart", "full"),
    _item("SpendChart", "half"),
    _item("FlowChart", "half"),
    _item("CategoryPie", "half"),
    _item("TagPie", "half"),
]

DEFAULT_LAYOUTS: dict[str, list[LayoutItem]] = {
    "desktop": DESKTOP_DEFAULT_LAYOUT,
    "mobile": MOBILE_DEFAULT_LAYOUT,
}


def default_layout_for(device_class: str) -> list[LayoutItem]:
    """Return a deep copy of the default layout for a device class."""
    return deepcopy(DEFAULT_LAYOUTS[device_class])


def sanitize_layout_for_read(layout: list[LayoutItem]) -> list[LayoutItem]:
    """Drop unknown widget_ids so removed catalog entries do not break reads."""
    return [item for item in layout if item.get("widget_id") in WIDGET_CATALOG_IDS]
