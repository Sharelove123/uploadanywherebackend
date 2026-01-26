from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Shared admin
    path('api/tenants/', include('apps.tenants.urls')),         # Tenant registration
    path('api/users/', include('apps.users.urls', namespace='users_public')), # Expose public user endpoints
    path('api/auth/', include('dj_rest_auth.urls')),            # Login/Logout (Public)
    path('api/payments/', include('apps.payments.urls', namespace='payments')), # Payments & Webhooks
]
