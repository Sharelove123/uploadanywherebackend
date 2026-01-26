"""
Main URL configuration for Content Repurposer project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def home(request):
    return Response({'message': 'Content Repurposer Backend is Running!', 'status': 'ok'})

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint with available routes."""
    return Response({
        'message': 'Welcome to Content Repurposer API',
        'version': '1.0.0',
        'endpoints': {
            'auth': {
                'login': '/api/auth/login/',
                'logout': '/api/auth/logout/',
                'user': '/api/auth/user/',
                'password_change': '/api/auth/password/change/',
                'token_refresh': '/api/auth/token/refresh/',
            },
            'users': '/api/users/',
            'repurposer': '/api/repurposer/',
            'social_accounts': '/api/social/',
            'payments': '/api/payments/',
            'admin': '/admin/',
        }
    })


urlpatterns = [
    # root
    path('', home, name='home'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Root
    path('api/', api_root, name='api-root'),
    
    # Authentication (dj-rest-auth)
    path('api/auth/', include('dj_rest_auth.urls')),
    
    # App URLs
    path('api/users/', include('apps.users.urls', namespace='users')),
    path('api/repurposer/', include('apps.repurposer.urls', namespace='repurposer')),
    path('api/social/', include('apps.social_accounts.urls', namespace='social_accounts')),
    path('api/payments/', include('apps.payments.urls', namespace='payments')),
    
    # DRF browsable API auth
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]

from django.conf import settings
from django.conf.urls.static import static

# Serve media files - needed for Instagram/Facebook to access uploaded images
# Note: For production, consider using a CDN or cloud storage (S3, Cloudinary)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
