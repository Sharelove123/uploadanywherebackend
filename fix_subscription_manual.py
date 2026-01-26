
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_tenant_model
from apps.payments.models import SubscriptionPlan
from apps.tenants.models import UserTenantMap

def fix_subscription(email, plan_name):
    print(f"--- Fixing subscription for {email} to verified plan '{plan_name}' ---")
    
    User = get_user_model()
    Tenant = get_tenant_model()  # Client model

    # 1. Get the Plan
    with schema_context('public'):
        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            print(f"ERROR: Plan '{plan_name}' not found in public schema.")
            print("Available plans:", list(SubscriptionPlan.objects.values_list('name', flat=True)))
            return
        print(f"Found plan: {plan.display_name} (ID: {plan.id})")

        # 2. Update Public User
        try:
            user = User.objects.get(email=email)
            user.subscription_tier = plan.name
            # Set dummy stripe IDs if missing, or keep existing if you have them. 
            # For manual fix, we mostly care about the tier.
            if not user.stripe_customer_id:
                user.stripe_customer_id = 'manual_fix_' + email
            user.save()
            print(f"SUCCESS: Updated Public User '{user.email}' to '{user.subscription_tier}'")
        except User.DoesNotExist:
            print(f"ERROR: User {email} not found in public schema.")
            return

        # 3. Update Tenant (The Missing Link)
        tenant_map = UserTenantMap.objects.filter(email=user.email).first()
        if tenant_map:
            tenant = tenant_map.tenant
            tenant.plan = plan
            tenant.save()
            print(f"SUCCESS: Updated Tenant '{tenant.schema_name}' plan to '{plan.name}'")
        else:
            print(f"WARNING: No Tenant found for user {email} in UserTenantMap.")

    # 4. Update User in ALL Tenants (Just in case)
    print("re-syncing user in all tenants...")
    tenants = Tenant.objects.exclude(schema_name='public')
    for t in tenants:
        try:
            with schema_context(t.schema_name):
                # Try finding by email
                tenant_user = User.objects.filter(email=email).first()
                if tenant_user:
                    tenant_user.subscription_tier = plan.name
                    tenant_user.save()
                    print(f" - Updated user in schema '{t.schema_name}'")
        except Exception as e:
            print(f"Error in schema {t.schema_name}: {e}")

    print("\nModification Complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fix_subscription_manual.py <email> <plan_name>")
        print("Example: python fix_subscription_manual.py abcd12@gmail.com pro")
    else:
        fix_subscription(sys.argv[1], sys.argv[2])
