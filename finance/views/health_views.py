from django.conf import settings
from django.http import JsonResponse


def api_health(request):
    """Lightweight liveness probe; includes PWA client-window hints when configured."""
    payload = {
        "status": "ok",
        "api_server_build": getattr(settings, "API_SERVER_BUILD", "dev"),
        "min_client_build_write": getattr(settings, "CLIENT_BUILD_MIN_WRITE", None),
    }
    return JsonResponse(payload)
