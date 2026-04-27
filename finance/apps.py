from django.apps import AppConfig

class FinanceConfig(AppConfig):
    name = "finance"

    def ready(self):
        import finance.api_tools.signals
        
        # Resolve JWT Serializer collisions in Spectacular schema by forcing unique ref_names.
        # Done here to avoid circular imports in settings.py.
        try:
            from rest_framework_simplejwt.serializers import TokenRefreshSerializer
            TokenRefreshSerializer.ref_name = 'SimpleJWTTokenRefresh'
        except ImportError:
            pass

        try:
            from dj_rest_auth.jwt_auth import CookieTokenRefreshSerializer
            CookieTokenRefreshSerializer.ref_name = 'DjRestAuthTokenRefresh'
        except ImportError:
            pass

        # Some refresh serializers can raise User.DoesNotExist when a refresh token
        # references a deleted user; convert this to auth failure instead of 500.
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.exceptions import InvalidToken
            from rest_framework_simplejwt.serializers import TokenRefreshSerializer
            from dj_rest_auth.jwt_auth import CookieTokenRefreshSerializer

            def _wrap_missing_user_validate(serializer_cls):
                if getattr(serializer_cls, "_finance_missing_user_wrapped", False):
                    return

                original_validate = serializer_cls.validate

                def _safe_validate(self, attrs):
                    try:
                        return original_validate(self, attrs)
                    except get_user_model().DoesNotExist as exc:
                        raise InvalidToken("No active account found for this token.") from exc

                serializer_cls.validate = _safe_validate
                serializer_cls._finance_missing_user_wrapped = True

            _wrap_missing_user_validate(TokenRefreshSerializer)
            _wrap_missing_user_validate(CookieTokenRefreshSerializer)
        except ImportError:
            pass
