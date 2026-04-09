
import logging
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import PaymentHistory, SubscriptionPlan

logger = logging.getLogger(__name__)


def _field(value, key, default=None):
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    try:
        return value[key]
    except Exception:
        return getattr(value, key, default)


def _get_session_email(session):
    customer_details = _field(session, 'customer_details', {}) or {}
    return (
        _field(customer_details, 'email')
        or _field(session, 'customer_email')
        or _field(_field(session, 'metadata', {}) or {}, 'user_email')
    )

@csrf_exempt
def stripe_webhook(request):
    logger.info("--- STRIPE WEBHOOK RECEIVED ---")
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    logger.info(f"Signature: {sig_header}")
    logger.info(f"Payload (start): {payload[:100]}")

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Event constructed successfully: {event['type']}")
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Unexpected error constructing event: {e}")
        return HttpResponse(status=400)

    # Handle the event
    logger.info(f"Processing event type: {event['type']}")
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        logger.info(f"Handling checkout session: {_field(session, 'id')}")
        handle_checkout_session(session)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        logger.info(f"Handling invoice payment: {_field(invoice, 'id')}")
        handle_invoice_payment_succeeded(invoice)
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        logger.info(f"Handling subscription deleted: {_field(subscription, 'id')}")
        handle_subscription_deleted(subscription)
    else:
        logger.info(f"Unhandled event type: {event['type']}")

    logger.info("--- WEBHOOK PROCESSED ---")
    return HttpResponse(status=200)

def handle_subscription_deleted(subscription):
    stripe_customer_id = _field(subscription, 'customer')
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
    stripe_customer_id = _field(invoice, 'customer')
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
    client_reference_id = _field(session, 'client_reference_id')
    stripe_customer_id = _field(session, 'customer')
    stripe_subscription_id = _field(session, 'subscription')
    metadata = _field(session, 'metadata', {}) or {}
    # Convert Stripe object to dict if necessary
    if not isinstance(metadata, dict):
        try:
            metadata = dict(metadata)
        except (TypeError, ValueError):
            metadata = {}
    user_email = _get_session_email(session)
    
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

    # 1. Update in Public if a shared user exists there
    try:
        with schema_context('public'):
            user = User.objects.filter(id=client_reference_id).first()
            if not user and user_email:
                user = User.objects.filter(email=user_email).first()

            if not user:
                logger.info("Public: No matching shared user found for checkout session %s", _field(session, 'id'))
            else:
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
                payment_ref = _field(session, 'payment_intent') or _field(session, 'id')
                PaymentHistory.objects.update_or_create(
                    stripe_payment_intent_id=payment_ref,
                    defaults={
                        'user': user,
                        'plan': plan,
                        'amount': _field(session, 'amount_total', 0) / 100.0,
                        'status': 'succeeded',
                    }
                )
                logger.info(f"Public: Subscription activated for user {user.username}")
    except Exception as e:
        logger.error(f"Public: Failed to sync shared user for checkout session {_field(session, 'id')}: {str(e)}")

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

                if tenant.plan_id != plan.id:
                    tenant.plan = plan
                    tenant.stripe_customer_id = stripe_customer_id
                    if stripe_subscription_id:
                        tenant.stripe_subscription_id = stripe_subscription_id
                    tenant.save()
                logger.info(f"{tenant.schema_name}: Subscription activated for user {user.username}")
        except Exception as e:
            logger.error(f"{tenant.schema_name}: Failed to update subscription: {str(e)}")
