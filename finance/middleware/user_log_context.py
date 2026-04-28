from django.conf import settings
from loguru import logger


class UserLogContextMiddleware:
    """
    Bind user identifiers into Loguru contextual extras for each request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        username = "anonymous"
        uid = "anonymous"

        if user is not None and getattr(user, "is_authenticated", False):
            profile = getattr(user, "appprofile", None)
            if profile is not None and getattr(profile, "user_id", None):
                uid = str(profile.user_id)
            if getattr(settings, "LOG_FULL_USERNAME", False):
                username = user.username or "anonymous"
            else:
                username = "authenticated"

        with logger.contextualize(uid=uid, username=username):
            return self.get_response(request)
