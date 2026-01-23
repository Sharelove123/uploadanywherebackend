from django.urls import path
from .views import ClientCreateView

urlpatterns = [
    path('register/', ClientCreateView.as_view(), name='tenant-register'),
]
