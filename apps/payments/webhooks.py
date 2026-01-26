
import logging
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import PaymentHistory, SubscriptionPlan

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    return HttpResponse(status=200)

def handle_subscription_deleted(subscription):
    stripe_customer_id = subscription.get('customer')
    User = get_user_model()
    from django_tenants.utils import get_tenant_model, schema_context
    Tenant = get_tenant_model()
    
    # 1. Update Public
    try:
        with schema_context('public'):
            user = User.objects.get(stripe_customer_id=stripe_customer_id)
            user.subscription_tier = 'free'
            user.save()
            logger.info(f"Public: Subscription cancelled for {user.username}")
    except User.DoesNotExist:
        pass

    # 2. Update Tenants
    tenants = Tenant.objects.exclude(schema_name='public')
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                user = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
                if user:
                    user.subscription_tier = 'free'
                    user.save()
                    logger.info(f"{tenant.schema_name}: Subscription cancelled for {user.username}")
        except Exception:
            pass

def handle_invoice_payment_succeeded(invoice):
    """Reset usage on successful plan renewal/payment."""
    stripe_customer_id = invoice.get('customer')
    # Use subscription ID to verify if needed, but simple payment success is enough for reset
    
    User = get_user_model()
    from django_tenants.utils import get_tenant_model, schema_context
    Tenant = get_tenant_model()

    logger.info(f"Processing renewal reset for customer {stripe_customer_id}")

    # 1. Reset Public
    try:
        with schema_context('public'):
            user = User.objects.get(stripe_customer_id=stripe_customer_id)
            user.repurposes_used_this_month = 0
            user.usage_reset_date = timezone.now().date()
            user.save()
            logger.info(f"Public: Usage reset for {user.username}")
    except User.DoesNotExist:
        pass

    # 2. Reset Tenants
    tenants = Tenant.objects.exclude(schema_name='public')
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                user = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
                if user:
                    user.repurposes_used_this_month = 0
                    user.usage_reset_date = timezone.now().date()
                    user.save()
                    logger.info(f"{tenant.schema_name}: Usage reset for {user.username}")
        except Exception as e:
            logger.error(f"{tenant.schema_name}: Failed to reset usage: {str(e)}")

def handle_checkout_session(session):
    client_reference_id = session.get('client_reference_id')
    stripe_customer_id = session.get('customer')
    stripe_subscription_id = session.get('subscription')
    metadata = session.get('metadata', {})
    
    User = get_user_model()
    from django_tenants.utils import get_tenant_model, schema_context
    Tenant = get_tenant_model()

    # We need to update this user in EVERY schema where they exist
    # First, get the plan (it's shared/public)
    plan_id = metadata.get('plan_id')
    plan = None
    if plan_id:
        with schema_context('public'):
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id)
            except SubscriptionPlan.DoesNotExist:
                logger.warning(f"Plan ID {plan_id} not found in DB")

    if not plan:
        return # Cannot proceed properly without plan

    # 1. Update in Public
    user_email = None
    try:
        with schema_context('public'):
            user = User.objects.get(id=client_reference_id)
            user_email = user.email
            user.subscription_tier = plan.name
            user.stripe_customer_id = stripe_customer_id
            if stripe_subscription_id:
                user.stripe_subscription_id = stripe_subscription_id
            user.save()
            
            # Update the Tenant (Client) Model
            # This is critical because the tenant model is often the source of truth for features
            from apps.tenants.models import UserTenantMap
            tenant_map = UserTenantMap.objects.filter(email=user.email).first()
            if tenant_map:
                tenant = tenant_map.tenant
                tenant.plan = plan
                tenant.stripe_customer_id = stripe_customer_id
                if stripe_subscription_id:
                    tenant.stripe_subscription_id = stripe_subscription_id
                tenant.save()
                logger.info(f"Public: Updated tenant {tenant.schema_name} plan to {plan.name}")

            # Log payment
            PaymentHistory.objects.create(
                user=user,
                plan=plan,
                amount=session.get('amount_total', 0) / 100.0,
                status='succeeded',
                stripe_payment_intent_id=session.get('payment_intent') or session.get('id')
            )
            logger.info(f"Public: Subscription activated for user {user.username}")
    except User.DoesNotExist:
        logger.warning(f"Public: User {client_reference_id} not found")
        return # If user not in public, can't sync email

    # 2. Update in All Tenants
    tenants = Tenant.objects.exclude(schema_name='public')
    for tenant in tenants:
        try:
            with schema_context(tenant.schema_name):
                # Try to find matching user by ID first
                user = User.objects.filter(id=client_reference_id).first()
                
                # Fallback to email if not found by ID
                if not user and user_email:
                    user = User.objects.filter(email=user_email).first()

                if not user:
                     continue
                
                user.subscription_tier = plan.name
                user.stripe_customer_id = stripe_customer_id
                if stripe_subscription_id:
                    user.stripe_subscription_id = stripe_subscription_id
                user.save()
                logger.info(f"{tenant.schema_name}: Subscription activated for user {user.username}")
        except Exception as e:
            logger.error(f"{tenant.schema_name}: Failed to update subscription: {str(e)}")
