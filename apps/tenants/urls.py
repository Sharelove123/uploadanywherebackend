from django.urls import path
from .views import ClientCreateView

app_name = 'tenants'

urlpatterns = [
    path('register/', ClientCreateView.as_view(), name='tenant-register'),
]
