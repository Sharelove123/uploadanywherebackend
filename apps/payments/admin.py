
from django.contrib import admin
from .models import SubscriptionPlan, PaymentHistory

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'price_monthly', 'price_yearly', 'is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    ordering = ('sort_order',)

@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'status', 'created_at')
    list_filter = ('status', 'plan', 'created_at')
    search_fields = ('user__username', 'user__email', 'stripe_payment_intent_id')
    readonly_fields = ('created_at',)
