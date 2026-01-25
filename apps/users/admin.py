"""
Admin configuration for users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin for CustomUser model."""
    list_display = ['username', 'email', 'subscription_tier', 'repurposes_used_this_month', 'is_staff', 'is_active']
    list_filter = ['subscription_tier', 'is_tenant_admin', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'stripe_customer_id']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Tenant Role', {
            'fields': ('is_tenant_admin',)
        }),
        ('Subscription', {
            'fields': ('subscription_tier', 'stripe_customer_id', 'stripe_subscription_id')
        }),
        ('Usage', {
            'fields': ('repurposes_used_this_month', 'usage_reset_date')
        }),
        ('Profile', {
            'fields': ('avatar', 'bio')
        }),
    )
