
from django.urls import path
from .views import SocialConnectView, SocialCallbackView

app_name = 'social_accounts'

urlpatterns = [
    path('connect/<str:platform>/', SocialConnectView.as_view(), name='social-connect'),
    path('callback/<str:platform>/', SocialCallbackView.as_view(), name='social-callback'),
]
