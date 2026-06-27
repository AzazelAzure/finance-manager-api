from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer

from finance.api_tools.tos import is_allowed_tos_version, record_tos_acceptance


class EmailUniqueRegisterSerializer(RegisterSerializer):
    """dj-rest-auth registration with case-insensitive email uniqueness and ToS clickwrap.

    The public ``POST /api/auth/registration/`` route must record Terms of Service
    acceptance with the same guarantees as the ``POST /finance/user/`` clickwrap path:
    a supported ``tos_version`` plus a server-set acceptance timestamp. The client
    timestamp (``tos_accepted_at``) is required as proof of intent but is never stored.
    """

    tos_version = serializers.CharField(max_length=20, required=True)
    tos_accepted_at = serializers.DateTimeField(required=True, write_only=True)

    def validate_email(self, email):
        email = super().validate_email(email)
        normalized = (email or "").strip().lower()
        if not normalized:
            return email
        User = get_user_model()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(
                _("A user is already registered with this e-mail address."),
            )
        return normalized

    def validate_tos_version(self, value):
        if not is_allowed_tos_version(value):
            raise serializers.ValidationError(_("Unsupported Terms of Service version."))
        return value

    def custom_signup(self, request, user):
        # Persist ToS acceptance with a server-set timestamp once the AppProfile exists
        # (created by the post_save signal during user.save()).
        record_tos_acceptance(user.appprofile, self.validated_data["tos_version"])
