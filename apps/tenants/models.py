from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Client(TenantMixin):
    """
    Represents a tenant (individual or company).
    Each tenant gets their own PostgreSQL schema.
    """
    class TenantType(models.TextChoices):
        INDIVIDUAL = 'individual', 'Individual'
        COMPANY = 'company', 'Company'
    
    name = models.CharField(max_length=100)
    tenant_type = models.CharField(
        max_length=20, 
        choices=TenantType.choices, 
        default=TenantType.INDIVIDUAL
    )
    
    # Billing info (tenant-level)
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    
    plan = models.ForeignKey(
        'payments.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    @property
    def subscription_tier(self):
        try:
            if self.plan_id and self.plan:
                return self.plan.name
        except Exception:
            # Plan might be in a different schema - query from public
            from django_tenants.utils import schema_context
            try:
                with schema_context('public'):
                    from apps.payments.models import SubscriptionPlan
                    plan = SubscriptionPlan.objects.get(id=self.plan_id)
                    return plan.name
            except Exception:
                pass
        return 'free'
    
    # Company-specific fields
    company_logo = models.URLField(blank=True)
    max_team_members = models.PositiveIntegerField(default=1)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Auto-create schema
    auto_create_schema = True

    def __str__(self):
        return f"{self.name} ({self.get_tenant_type_display()})"


class Domain(DomainMixin):
    """
    Domain/subdomain for tenant routing.
    e.g., john.uploadanywhere.com or acme.uploadanywhere.com
    """
    pass
