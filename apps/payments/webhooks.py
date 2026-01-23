
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
        # Extend subscription logic if needed (usually handled by subscription status)
        pass
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)

    return HttpResponse(status=200)

def handle_subscription_deleted(subscription):
    stripe_customer_id = subscription.get('customer')
    User = get_user_model()
    
    try:
        user = User.objects.get(stripe_customer_id=stripe_customer_id)
        # Downgrade to Free
        user.subscription_tier = 'free'
        user.save()
        logger.info(f"Subscription expired/cancelled for user {user.username}. Downgraded to Free.")
        
    except User.DoesNotExist:
        logger.warning(f"User not found for subscription deletion: {stripe_customer_id}")

def handle_checkout_session(session):
    client_reference_id = session.get('client_reference_id')
    stripe_customer_id = session.get('customer')
    stripe_subscription_id = session.get('subscription')
    metadata = session.get('metadata', {})
    
    User = get_user_model()
    try:
        user = User.objects.get(id=client_reference_id)
        
        # Get Plan from metadata
        plan_id = metadata.get('plan_id')
        plan = None
        
        if plan_id:
            try:
                # Try to find plan by ID
                plan = SubscriptionPlan.objects.get(id=plan_id)
            except (SubscriptionPlan.DoesNotExist, ValueError):
                # Fallback: try finding by looking up via price in session (complex, skip for now)
                logger.warning(f"Plan ID {plan_id} not found in DB")
        
        if plan:
            user.subscription_tier = plan.name
            
        user.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            user.stripe_subscription_id = stripe_subscription_id
            
        user.save()
        
        # Log payment
        PaymentHistory.objects.create(
            user=user,
            plan=plan,
            amount=session.get('amount_total', 0) / 100.0, # Convert cents to dollars
            status='succeeded',
            stripe_payment_intent_id=session.get('payment_intent') or session.get('id')
        )
        
        logger.info(f"Subscription activated for user {user.username} to plan {plan.name if plan else 'Unknown'}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for payment: {client_reference_id}")
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
