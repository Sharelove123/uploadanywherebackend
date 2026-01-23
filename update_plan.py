"""Script to update tenant plan after purchase."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context
from apps.tenants.models import Client
from apps.payments.models import SubscriptionPlan, PaymentHistory

# Update abcd tenant to Pro plan
try:
    tenant = Client.objects.get(schema_name='abcd')
    
    # Get Pro plan from public schema
    with schema_context('public'):
        pro_plan = SubscriptionPlan.objects.get(name='pro')
        print(f"Found Pro plan: {pro_plan.display_name} - ${pro_plan.price_monthly}/mo")
    
    # Update tenant's plan
    tenant.plan = pro_plan
    tenant.save()
    print(f"Updated tenant '{tenant.name}' to plan: {pro_plan.display_name}")
    
    # Create payment history in tenant schema
    with schema_context('abcd'):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.first()
        
        if user:
            PaymentHistory.objects.create(
                user=user,
                plan=pro_plan,
                amount=pro_plan.price_monthly,
                status='succeeded',
                stripe_payment_intent_id='test_purchase_manual'
            )
            print(f"Created payment history for user: {user.username}")
        
except Client.DoesNotExist:
    print("Tenant 'abcd' not found")
except SubscriptionPlan.DoesNotExist:
    print("Pro plan not found")
except Exception as e:
    print(f"Error: {e}")

print("\nDone!")
