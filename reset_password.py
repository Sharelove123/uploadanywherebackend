"""Script to list/reset tenant admin passwords."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Client, Domain

# List all tenants
print("=== All Tenants ===")
for client in Client.objects.all():
    print(f"  {client.schema_name}: {client.name}")
    for domain in Domain.objects.filter(tenant=client):
        print(f"    - {domain.domain}")
        
# Check abcd tenant users
print("\n=== Users in 'abcd' tenant ===")
try:
    abcd_tenant = Client.objects.get(schema_name='abcd')
    with schema_context('abcd'):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        for user in User.objects.all():
            print(f"  Username: {user.username}, Email: {user.email}")
            # Reset password to 'password123'
            user.set_password('password123')
            user.save()
            print(f"    -> Password reset to: password123")
except Client.DoesNotExist:
    print("  No 'abcd' tenant found")
except Exception as e:
    print(f"  Error: {e}")

print("\nDone!")
