"""
URL configuration for repurposer app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'repurposer'

router = DefaultRouter()
router.register(r'brand-voices', views.BrandVoiceViewSet, basename='brand-voice')
router.register(r'sources', views.ContentSourceViewSet, basename='source')
router.register(r'posts', views.RepurposedPostViewSet, basename='post')
router.register(r'scheduled-posts', views.ScheduledPostViewSet, basename='scheduled-post')

urlpatterns = [
    path('', include(router.urls)),
    path('repurpose/', views.RepurposeView.as_view(), name='repurpose'),
]
