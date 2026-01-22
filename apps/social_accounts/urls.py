"""
URL configuration for social_accounts app.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
# from . import views

app_name = 'social_accounts'

# TODO: Add social account views
urlpatterns = [
    # path('', views.SocialAccountListView.as_view(), name='list'),
    # path('connect/<str:platform>/', views.OAuthConnectView.as_view(), name='connect'),
    # path('callback/<str:platform>/', views.OAuthCallbackView.as_view(), name='callback'),
    # path('<int:pk>/disconnect/', views.DisconnectView.as_view(), name='disconnect'),
]
