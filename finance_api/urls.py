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
from django.urls import path, include
from django.http import JsonResponse
from finance.views.cat_views import CategoryListCreateView, CategoryDetailView
from finance.views.exp_views import UpcomingExpenseListCreateView, UpcomingExpenseDetailView
from finance.views.profile_views import AppProfileView, AppProfileSnapshotView
from finance.views.src_views import SourceListCreateView, SourceDetailView
from finance.views.tag_views import TagView
from finance.views.tx_views import TransactionListCreateView, TransactionDetailView
from finance.views.usr_views import UserView
from finance.views.auth_views import GoogleLogin, GitHubLogin
from finance.views.report_views import BugReportView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework_simplejwt.serializers import TokenRefreshSerializer # Added for subclassing
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema_serializer # Added for schema customization


# Custom serializer and view to resolve drf_spectacular warnings about identical component names
@extend_schema_serializer(component_name="SimpleJWTTokenRefresh")
class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Custom TokenRefreshSerializer to provide a unique component name for drf_spectacular.
    This resolves warnings about multiple schemas with the same name (TokenRefreshRequest).
    """
    pass

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom TokenRefreshView to use the CustomTokenRefreshSerializer.
    """
    serializer_class = CustomTokenRefreshSerializer


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", lambda request: JsonResponse({"status": "ok"}), name="health"),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'), # Modified to use CustomTokenRefreshView
    path('api/token/auth/', TokenObtainPairView.as_view(), name='token_auth'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Auth & Social Login
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('api/auth/github/', GitHubLogin.as_view(), name='github_login'),
    path("finance/transactions/", TransactionListCreateView.as_view(), name="transactions_list_create"),
    path("finance/transactions/<str:tx_id>/", TransactionDetailView.as_view(), name="transaction_detail"),
    path("finance/appprofile/", AppProfileView.as_view(), name="appprofile"),
    path("finance/appprofile/snapshot/", AppProfileSnapshotView.as_view(), name="appprofile_snapshot"),
    path("finance/sources/", SourceListCreateView.as_view(), name="sources_list_create"),
    path("finance/sources/<str:source>/", SourceDetailView.as_view(), name="source_detail"),
    path("finance/upcoming_expenses/", UpcomingExpenseListCreateView.as_view(), name="upcoming_expenses_list_create"),
    path("finance/upcoming_expenses/<str:name>/", UpcomingExpenseDetailView.as_view(), name="upcoming_expense_detail"),
    path("finance/categories/", CategoryListCreateView.as_view(), name="categories_list_create"),
    path("finance/categories/<str:cat_name>/", CategoryDetailView.as_view(), name="category_detail"),
    path("finance/tags/", TagView.as_view(), name="tags"), 
    path("finance/user/", UserView.as_view(), name="user"), 
    path("finance/bug-report/", BugReportView.as_view(), name="bug_report"),
]