from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import remove_www

class HeaderTenantMiddleware(TenantMainMiddleware):
    """
    Middleware that selects the tenant based on the 'X-Tenant-Domain' header
    if present. Otherwise falls back to the Host header.
    
    Security Note:
    Spoofing this header is equivalent to spoofing the Host header.
    Access to data is still protected by Authentication and Permissions tiers.
    """
    def hostname_from_request(self, request):
        # Look for the custom header first
        tenant_header = request.headers.get('X-Tenant-Domain')
        if tenant_header:
            return remove_www(tenant_header)
        
        # Fallback to standard behavior
        return remove_www(request.get_host())
