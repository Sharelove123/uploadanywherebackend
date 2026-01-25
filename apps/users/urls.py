"""
URL configuration for users app.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('usage/', views.UsageStatsView.as_view(), name='usage-stats'),
    path('tenant-lookup/', views.TenantLookupView.as_view(), name='tenant-lookup'),
]
