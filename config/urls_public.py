from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Shared admin
    path('api/tenants/', include('apps.tenants.urls')),         # Tenant registration
    path('api/auth/', include('dj_rest_auth.urls')),            # Login/Logout (Public)
]
