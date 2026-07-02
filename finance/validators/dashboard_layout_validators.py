"""Validators for dashboard layout persistence (F-006 T01)."""

from functools import wraps

from rest_framework.exceptions import ValidationError

from finance.logic.dashboard_layout import DEVICE_CLASSES, SIZE_TIERS, WIDGET_CATALOG_IDS


def _validate_device_class(device_class: str) -> str:
    normalized = str(device_class).strip().lower()
    if normalized not in DEVICE_CLASSES:
        raise ValidationError("device_class must be 'mobile' or 'desktop'")
    return normalized


def _validate_layout(layout) -> list[dict]:
    if not isinstance(layout, list):
        raise ValidationError("layout must be a list")
    if len(layout) > 32:
        raise ValidationError("layout exceeds maximum widget count")
    seen: set[str] = set()
    normalized: list[dict] = []
    for index, item in enumerate(layout):
        if not isinstance(item, dict):
            raise ValidationError(f"layout[{index}] must be an object")
        widget_id = item.get("widget_id")
        if not isinstance(widget_id, str) or not widget_id.strip():
            raise ValidationError(f"layout[{index}].widget_id is required")
        widget_id = widget_id.strip()
        if widget_id not in WIDGET_CATALOG_IDS:
            raise ValidationError(f"Unknown widget_id: {widget_id}")
        if widget_id in seen:
            raise ValidationError(f"Duplicate widget_id: {widget_id}")
        seen.add(widget_id)
        size = item.get("size", "full")
        if size not in SIZE_TIERS:
            raise ValidationError(f"layout[{index}].size must be 'full' or 'half'")
        visible = item.get("visible", True)
        if not isinstance(visible, bool):
            raise ValidationError(f"layout[{index}].visible must be a boolean")
        normalized.append({"widget_id": widget_id, "size": size, "visible": visible})
    return normalized


def DashboardLayoutDeviceValidator(func):
    """Validate device_class query/body parameter."""

    @wraps(func)
    def _wrapped(uid, device_class, *args, **kwargs):
        validated = _validate_device_class(device_class)
        return func(uid, validated, *args, **kwargs)

    return _wrapped


def DashboardLayoutUpsertValidator(func):
    """Validate upsert payload (device_class + layout)."""

    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        if not isinstance(data, dict):
            raise ValidationError("Request body must be an object")
        if "device_class" not in data:
            raise ValidationError("device_class is required")
        if "layout" not in data:
            raise ValidationError("layout is required")
        kwargs["device_class"] = _validate_device_class(data["device_class"])
        kwargs["layout"] = _validate_layout(data["layout"])
        return func(uid, data, *args, **kwargs)

    return _wrapped
