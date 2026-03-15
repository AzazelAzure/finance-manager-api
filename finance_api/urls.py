
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
from django.urls import path
from finance.views.cat_views import CategoryView
from finance.views.exp_views import UpcomingExpenseView
from finance.views.profile_views import AppProfileView
from finance.views.src_views import SourceView
from finance.views.tag_views import TagView
from finance.views.tx_views import TransactionView
from finance.views.usr_views import UserView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/auth/', TokenObtainPairView.as_view(), name='token_auth'),
    path('api/token/verify/', TokenRefreshView.as_view(), name='token_verify'),
    path("finance/transactions/", TransactionView.as_view(), name="transactions_list_create"), # Handles GET (list with filters) and POST (new transaction)
    path("finance/transactions/<str:tx_id>/", TransactionView.as_view(), name="transaction_detail_update_delete"), # Handles GET (single), PUT, DELETE
    path("finance/appprofile/", AppProfileView.as_view(), name="appprofile"), # Handles GET (single)
    path("finance/appprofile/snapshot/", AppProfileView.as_view(), name="appprofile_snapshot"), # Handles GET with snapshot bool
    path("finance/sources/", SourceView.as_view(), name="sources"), # Handles GET (list with filters) and POST (new source)
    path("finance/sources/<str:source>/", SourceView.as_view(), name="source_detail_update_delete"), # Handles GET (single), PUT, DELETE
    path("finance/upcoming_expenses/", UpcomingExpenseView.as_view(), name="upcoming_expenses"), # Handles GET (list with filters) and POST (new expense)
    path("finance/upcoming_expenses/<str:name>/", UpcomingExpenseView.as_view(), name="upcoming_expense_detail_update_delete"), # Handles GET (single), PUT, DELETE
    path("finance/categories/", CategoryView.as_view(), name="categories"), # Handles GET (list with filters) and POST (new category)
    path("finance/categories/<str:cat_name>/", CategoryView.as_view(), name="category_detail_update_delete"), # Handles GET (single), PUT, DELETE
    path("finance/tags/", TagView.as_view(), name="tags"), 
    path("finance/user/", UserView.as_view(), name="user"), 
]
