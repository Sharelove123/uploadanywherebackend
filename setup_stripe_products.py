
import os
import sys
import django
import stripe

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import dotenv
dotenv.load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.payments.models import SubscriptionPlan
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def setup_products():
    print(f"Using Stripe Key: {stripe.api_key[:8]}...")
    
    plans_config = [
        {
            'name': 'pro',
            'product_name': 'Repurpose.ai Pro',
            'price_monthly': 1900, # cents
            'price_yearly': 19000,
        },
        {
            'name': 'agency',
            'product_name': 'Repurpose.ai Agency',
            'price_monthly': 5900,
            'price_yearly': 59000,
        }
    ]

    for p_conf in plans_config:
        try:
            print(f"Setting up {p_conf['product_name']}...")
            
            # 1. Create Product
            product = stripe.Product.create(name=p_conf['product_name'])
            
            # 2. Create Monthly Price
            price_mo = stripe.Price.create(
                unit_amount=p_conf['price_monthly'],
                currency='usd',
                recurring={'interval': 'month'},
                product=product.id,
            )
            
            # 3. Create Yearly Price
            price_yr = stripe.Price.create(
                unit_amount=p_conf['price_yearly'],
                currency='usd',
                recurring={'interval': 'year'},
                product=product.id,
            )
            
            # 4. Update Local DB
            try:
                plan = SubscriptionPlan.objects.get(name=p_conf['name'])
                plan.stripe_price_id_monthly = price_mo.id
                plan.stripe_price_id_yearly = price_yr.id
                plan.save()
                print(f"Updated {p_conf['name']} with Monthly: {price_mo.id}, Yearly: {price_yr.id}")
            except SubscriptionPlan.DoesNotExist:
                print(f"Error: Local plan '{p_conf['name']}' not found in DB. Run seed_plans.py first.")

        except Exception as e:
            print(f"Failed to setup {p_conf['name']}: {str(e)}")

if __name__ == "__main__":
    setup_products()
