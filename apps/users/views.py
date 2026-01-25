"""
API Views for User management.
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'User registered successfully.',
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update current user's profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change password endpoint."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        return Response({'message': 'Password changed successfully.'})


class UsageStatsView(APIView):
    """Get user's usage statistics."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.conf import settings
        
        limits = settings.SUBSCRIPTION_LIMITS.get(user.subscription_tier, {})
        max_repurposes = limits.get('repurposes_per_month', 0)
        
        return Response({
            'subscription_tier': user.subscription_tier,
            'repurposes_used': user.repurposes_used_this_month,
            'repurposes_limit': max_repurposes,
            'repurposes_remaining': max_repurposes - user.repurposes_used_this_month if max_repurposes != -1 else -1,
            'can_repurpose': user.can_repurpose(),
            'features': {
                'brand_voices': limits.get('brand_voices', 0),
                'direct_posting': limits.get('direct_posting', False),
                'platforms': limits.get('platforms', []),
            }
        })


class TenantLookupView(APIView):
    """
    Public endpoint to lookup user's tenant by email.
    Used for redirection during login.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # We need to look into PUBLIC schema
        from django_tenants.utils import schema_context
        from apps.tenants.models import UserTenantMap
        
        try:
            with schema_context('public'):
                mapping = UserTenantMap.objects.get(email=email)
                
                # Get primary domain for this tenant
                domains = mapping.tenant.domains.all()
                primary_domain = domains.filter(is_primary=True).first() or domains.first()
                
                if not primary_domain:
                    return Response({'error': 'Tenant found but no domain configured.'}, status=status.HTTP_404_NOT_FOUND)
                
                return Response({
                    'found': True,
                    'tenant_name': mapping.tenant.name,
                    'tenant_domain': primary_domain.domain
                })
        except UserTenantMap.DoesNotExist:
            return Response({'found': False, 'message': 'No tenant mapping found.'}, status=status.HTTP_200_OK)
