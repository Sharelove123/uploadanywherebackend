
from django.urls import path
from .views import CreateCheckoutSessionView, SubscriptionPlansView
from .webhooks import stripe_webhook

app_name = 'payments'

urlpatterns = [
    path('plans/', SubscriptionPlansView.as_view(), name='subscription-plans'),
    path('create-checkout-session/', CreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('webhook/', stripe_webhook, name='stripe-webhook'),
]
