from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer


class EmailUniqueRegisterSerializer(RegisterSerializer):
    """dj-rest-auth registration with case-insensitive email uniqueness vs User rows."""

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
