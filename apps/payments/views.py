
import logging
import stripe
from django.conf import settings
from django.utils import timezone
from rest_framework import views, status, permissions
from rest_framework.response import Response
from .models import SubscriptionPlan

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateCheckoutSessionView(views.APIView):
    """
    Creates a Stripe Checkout Session for a subscription.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django_tenants.utils import schema_context
        
        plan_id = request.data.get('plan_id') # e.g. price_123 or internal ID
        interval = request.data.get('interval', 'monthly') # 'monthly' or 'yearly'
        
        try:
            # Look up internal plan to get Stripe Price ID
            # Plans are stored in public schema
            if str(plan_id).isdigit():
                with schema_context('public'):
                    plan = SubscriptionPlan.objects.get(id=plan_id)
                    price_id = plan.stripe_price_id_yearly if interval == 'yearly' else plan.stripe_price_id_monthly
            else:
                # If plan_id is already a stripe ID (e.g. from frontend hardcoded)
                price_id = plan_id 
                
            if not price_id:
                return Response({'error': 'Invalid plan or configuration missing price ID'}, status=status.HTTP_400_BAD_REQUEST)

            # Build return URLs using the request origin (tenant subdomain)
            # This ensures users return to their tenant subdomain after checkout
            origin = request.META.get('HTTP_ORIGIN', settings.FRONTEND_URL)
            if not origin:
                # Fallback: build from request host
                origin = f"http://{request.get_host().replace(':8000', ':3000')}"
            
            checkout_session = stripe.checkout.Session.create(
                customer_email=request.user.email,
                client_reference_id=str(request.user.id),
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=origin + '/dashboard/subscription?success=true',
                cancel_url=origin + '/dashboard/subscription?canceled=true',
                metadata={
                    'user_id': request.user.id,
                    'plan_id': plan_id,
                }
            )
            
            return Response({'sessionId': checkout_session.id, 'url': checkout_session.url})
            
        except SubscriptionPlan.DoesNotExist:
             return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Stripe Checkout Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionPlansView(views.APIView):
    """List available subscription plans."""
    permission_classes = [permissions.AllowAny] # Public info

    def get(self, request):
        from django_tenants.utils import schema_context
        
        # Plans are stored in the public schema, so query explicitly
        with schema_context('public'):
            plans = SubscriptionPlan.objects.filter(is_active=True)
            # Serialize manually or use serializer
            data = [{
                'id': p.id,
                'name': p.name,
                'display_name': p.display_name,
                'price_monthly': str(p.price_monthly),
                'price_yearly': str(p.price_yearly),
                'features': {
                    'repurposes': p.repurposes_per_month,
                    'brand_voices': p.brand_voices_limit,
                    'direct_posting': p.direct_posting
                },
                'stripe_price_id_monthly': p.stripe_price_id_monthly
            } for p in plans]
        return Response(data)
