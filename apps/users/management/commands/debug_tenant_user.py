from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, schema_context

class Command(BaseCommand):
    help = 'Debug user across tenants'

    def handle(self, *args, **options):
        Tenant = get_tenant_model()
        User = get_user_model()
        
        # Check Public Schema first (usually where shared users are if configured that way)
        self.stdout.write("\n=== SCHEMA: public ===")
        with schema_context('public'):
             user = User.objects.filter(email='raworkemai1253@gmail.com').first()
             if user:
                 self.stdout.write(f"User Found (ID: {user.id})")
                 self.stdout.write(f"Tier: '{user.subscription_tier}'")
             else:
                 self.stdout.write("User NOT found in public.")

        # Check all tenants
        tenants = Tenant.objects.exclude(schema_name='public')
        for tenant in tenants:
            self.stdout.write(f"\n=== SCHEMA: {tenant.schema_name} ({tenant.name}) ===")
            with schema_context(tenant.schema_name):
                user = User.objects.filter(email='raworkemai1253@gmail.com').first()
                if user:
                    self.stdout.write(f"User Found (ID: {user.id})")
                    self.stdout.write(f"Tier: '{user.subscription_tier}'")
                    
                    # Force update if found and wrong
                    if user.subscription_tier != 'pro':
                        self.stdout.write("UPDATING TO PRO...")
                        user.subscription_tier = 'pro'
                        user.save()
                        self.stdout.write("UPDATED.")
                else:
                    self.stdout.write("User NOT found in this schema.")
