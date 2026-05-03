"""
URL configuration for hive_hub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import path, include
from finance.views.health_views import api_health
from finance.views.cat_views import CategoryListCreateView, CategoryDetailView
from finance.views.exp_views import UpcomingExpenseListCreateView, UpcomingExpenseDetailView
from finance.views.profile_views import AppProfileView, AppProfileSnapshotView
from finance.views.src_views import SourceListCreateView, SourceDetailView
from finance.views.tag_views import TagView
from finance.views.tx_views import (
    TransactionCalendarView,
    TransactionDetailView,
    TransactionListCreateView,
    TransactionVisualizationView,
)
from finance.views.usr_views import UserView
from finance.views.auth_views import GoogleLogin, GitHubLogin
from finance.views.report_views import BugReportView
from finance.views.exchange_views import ExchangeRatesMatrixView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer # Added for subclassing
from rest_framework_simplejwt.exceptions import InvalidToken
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema_serializer # Added for schema customization
# Custom serializer and view to resolve drf_spectacular warnings about identical component names
@extend_schema_serializer(component_name="SimpleJWTTokenRefresh")
class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Custom TokenRefreshSerializer to provide a unique component name for drf_spectacular.
    This resolves warnings about multiple schemas with the same name (TokenRefreshRequest).
    """
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist as exc:
            # Missing/deleted users should produce auth failure, not a 500.
            raise InvalidToken("No active account found for this token.") from exc


@extend_schema_serializer(component_name="SimpleJWTTokenObtainPair")
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allow token login using username or email identifier."""

    def validate(self, attrs):
        identifier = str(attrs.get(self.username_field, "")).strip()
        attrs = dict(attrs)
        attrs[self.username_field] = identifier
        if identifier:
            if "@" in identifier:
                user = get_user_model().objects.filter(email__iexact=identifier).first()
            else:
                user = get_user_model().objects.filter(username__iexact=identifier).first()
            if user is not None:
                attrs[self.username_field] = getattr(user, self.username_field)
        return super().validate(attrs)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Use serializer that accepts username or email identifier."""

    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom TokenRefreshView to use the CustomTokenRefreshSerializer.
    """
    serializer_class = CustomTokenRefreshSerializer


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", api_health, name="health"),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'), # Modified to use CustomTokenRefreshView
    path('api/token/auth/', CustomTokenObtainPairView.as_view(), name='token_auth'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Auth & Social Login
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('api/auth/github/', GitHubLogin.as_view(), name='github_login'),
    path("finance/transactions/", TransactionListCreateView.as_view(), name="transactions_list_create"),
    path("finance/transactions/calendar/", TransactionCalendarView.as_view(), name="transactions_calendar"),
    path("finance/transactions/visualization/", TransactionVisualizationView.as_view(), name="transactions_visualization"),
    path("finance/transactions/<str:tx_id>/", TransactionDetailView.as_view(), name="transaction_detail"),
    path("finance/appprofile/", AppProfileView.as_view(), name="appprofile"),
    path("finance/appprofile/snapshot/", AppProfileSnapshotView.as_view(), name="appprofile_snapshot"),
    path("finance/exchange_rates/", ExchangeRatesMatrixView.as_view(), name="finance_exchange_rates"),
    path("finance/sources/", SourceListCreateView.as_view(), name="sources_list_create"),
    path("finance/sources/<str:source>/", SourceDetailView.as_view(), name="source_detail_update_delete"),
    path("finance/upcoming_expenses/", UpcomingExpenseListCreateView.as_view(), name="upcoming_expenses"),
    path("finance/upcoming_expenses/<str:name>/", UpcomingExpenseDetailView.as_view(), name="upcoming_expense_detail_update_delete"),
    path("finance/categories/", CategoryListCreateView.as_view(), name="categories"),
    path("finance/categories/<str:cat_name>/", CategoryDetailView.as_view(), name="category_detail_update_delete"),
    path("finance/tags/", TagView.as_view(), name="tags"), 
    path("finance/user/", UserView.as_view(), name="user"), 
    path("finance/bug-report/", BugReportView.as_view(), name="bug_report"),
]