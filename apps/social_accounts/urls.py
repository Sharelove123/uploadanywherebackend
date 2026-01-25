
from django.urls import path
from .views import SocialConnectView, SocialCallbackView, SocialAccountListView, SocialDisconnectView

app_name = 'social_accounts'

urlpatterns = [
    path('', SocialAccountListView.as_view(), name='social-list'),
    path('connect/<str:platform>/', SocialConnectView.as_view(), name='social-connect'),
    path('callback/<str:platform>/', SocialCallbackView.as_view(), name='social-callback'),
    path('disconnect/<str:platform>/', SocialDisconnectView.as_view(), name='social-disconnect'),
]
