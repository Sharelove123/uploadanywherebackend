"""
Models for subscription and payment tracking.
"""
from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    """Available subscription plans."""
    
    name = models.CharField(max_length=50, unique=True)  # 'free', 'pro', 'agency'
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_price_id_monthly = models.CharField(max_length=255, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=255, blank=True)
    
    # Features
    repurposes_per_month = models.IntegerField(default=0, help_text="-1 for unlimited")
    brand_voices_limit = models.IntegerField(default=0, help_text="-1 for unlimited")
    direct_posting = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return self.display_name


class PaymentHistory(models.Model):
    """Record of all payments."""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Stripe references
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True)
    
    # Billing period
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment History'
        verbose_name_plural = 'Payment History'

    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"
