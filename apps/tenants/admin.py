from django.contrib import admin
from django_tenants.admin import TenantAdminMixin
from .models import Client, Domain, UserTenantMap

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'schema_name', 'tenant_type', 'created_at', 'is_active')
    search_fields = ('name', 'schema_name')
    list_filter = ('tenant_type', 'is_active')

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    search_fields = ('domain', 'tenant__name')
    list_filter = ('is_primary',)

@admin.register(UserTenantMap)
class UserTenantMapAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'created_at')
    search_fields = ('email', 'tenant__name')
