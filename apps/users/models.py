"""
Custom User model with subscription tracking.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Extended user model with subscription and usage tracking."""
    
    is_tenant_admin = models.BooleanField(default=False, help_text="Can manage tenant settings and members.")
    
    # Usage tracking (resets monthly)
    repurposes_used_this_month = models.PositiveIntegerField(default=0)
    usage_reset_date = models.DateField(null=True, blank=True)
    
    # Profile
    avatar = models.URLField(blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email or self.username
    
    def can_repurpose(self) -> bool:
        """Check if user has remaining repurposes this month (based on Tenant plan)."""
        from django.conf import settings
        from django.db import connection
        
        tenant = connection.tenant
        # Default to 'free' if tenant has no subscription tier set
        tier = getattr(tenant, 'subscription_tier', 'free')
        
        limits = settings.SUBSCRIPTION_LIMITS.get(tier, {})
        max_repurposes = limits.get('repurposes_per_month', 0)
        
        if max_repurposes == -1:  # Unlimited
            return True
        return self.repurposes_used_this_month < max_repurposes
    
    def increment_usage(self):
        """Increment the repurpose usage count."""
        self.repurposes_used_this_month += 1
        self.save(update_fields=['repurposes_used_this_month'])
