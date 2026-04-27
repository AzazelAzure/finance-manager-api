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
