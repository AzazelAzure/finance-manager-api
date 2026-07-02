"""Service layer for dashboard layout persistence (F-006 T01)."""

from django.db import transaction

import finance.logic.validators as validator
from finance.logic.dashboard_layout import default_layout_for, sanitize_layout_for_read
from finance.models import DashboardLayout
from finance.validators.dashboard_layout_validators import (
    DashboardLayoutDeviceValidator,
    DashboardLayoutUpsertValidator,
)


def _layout_payload(device_class: str, layout: list, *, is_default: bool, updated_at=None) -> dict:
    payload = {
        "device_class": device_class,
        "layout": layout,
        "is_default": is_default,
    }
    if updated_at is not None:
        payload["updated_at"] = updated_at.isoformat()
    return payload


@validator.UserValidator
@DashboardLayoutDeviceValidator
def get_dashboard_layout(uid, device_class, *args, **kwargs):
    """Return saved layout for the variant or the device-appropriate default."""
    row = DashboardLayout.objects.filter(uid=uid, device_class=device_class).first()
    if row is None:
        return _layout_payload(device_class, default_layout_for(device_class), is_default=True)
    return _layout_payload(
        device_class,
        sanitize_layout_for_read(row.layout),
        is_default=False,
        updated_at=row.updated_at,
    )


@validator.UserValidator
@DashboardLayoutUpsertValidator
@transaction.atomic
def upsert_dashboard_layout(uid, data, *args, **kwargs):
    """Create or replace the layout for one device class."""
    device_class = kwargs["device_class"]
    layout = kwargs["layout"]
    row, _created = DashboardLayout.objects.update_or_create(
        uid=uid,
        device_class=device_class,
        defaults={"layout": layout},
    )
    row.refresh_from_db(fields=["updated_at"])
    return _layout_payload(
        device_class,
        sanitize_layout_for_read(row.layout),
        is_default=False,
        updated_at=row.updated_at,
    )


@validator.UserValidator
@DashboardLayoutDeviceValidator
@transaction.atomic
def reset_dashboard_layout(uid, device_class, *args, **kwargs):
    """Delete saved layout for one variant; subsequent GET returns the default."""
    DashboardLayout.objects.filter(uid=uid, device_class=device_class).delete()
    return _layout_payload(device_class, default_layout_for(device_class), is_default=True)
