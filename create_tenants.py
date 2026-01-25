import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenants.models import Client, Domain

def create_tenants():
    # 1. Public Tenant
    if not Client.objects.filter(schema_name='public').exists():
        print("Creating Public Tenant...")
        public_tenant = Client(schema_name='public', name='Public Tenant', tenant_type='company')
        public_tenant.save()
        
        domain = Domain()
        domain.domain = 'localhost' # or whatever DEFAULT_TENANT_DOMAIN is
        domain.tenant = public_tenant
        domain.is_primary = True
        domain.save()
        print("Public Tenant created.")
    else:
        print("Public Tenant already exists.")

    # 2. Test Tenant
    if not Client.objects.filter(schema_name='test').exists():
        print("Creating Test Tenant...")
        test_tenant = Client(schema_name='test', name='Test Company', tenant_type='company')
        test_tenant.save()
        
        domain = Domain()
        domain.domain = 'test.localhost'
        domain.tenant = test_tenant
        domain.is_primary = True
        domain.save()
        
        # Create map for default admin user
        from apps.tenants.models import UserTenantMap
        UserTenantMap.objects.create(email='admin@test.localhost', tenant=test_tenant)
        
        print("Test Tenant created.")
    else:
        print("Test Tenant already exists.")

if __name__ == '__main__':
    create_tenants()
