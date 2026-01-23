from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import remove_www, get_public_schema_name
from django.db import connection


class HeaderTenantMiddleware(TenantMainMiddleware):
    """
    Middleware that selects the tenant based on the 'X-Tenant-Domain' header
    if present. Otherwise falls back to the Host header.
    
    If the domain is not found in the database, it falls back to the public tenant
    instead of raising an error. This is crucial for Vercel/Render deployments
    where the frontend domain may not be pre-registered.
    """
    def hostname_from_request(self, request):
        # Look for the custom header first
        tenant_header = request.headers.get('X-Tenant-Domain')
        if tenant_header:
            return remove_www(tenant_header)
        
        # Fallback to standard behavior
        return remove_www(request.get_host())

    def get_tenant(self, domain_model, hostname):
        """
        Override to fall back to public tenant if domain not found.
        """
        try:
            return super().get_tenant(domain_model, hostname)
        except domain_model.DoesNotExist:
            # Domain not found - fall back to public tenant
            # This ensures public endpoints work even if frontend domain isn't registered
            public_domain = domain_model.objects.filter(
                tenant__schema_name=get_public_schema_name()
            ).first()
            
            if public_domain:
                return public_domain.tenant  # Return the tenant, not the domain!
            else:
                # If no public domain exists at all, re-raise the original error
                raise

