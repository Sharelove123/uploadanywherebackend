import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from apps.payments.models import SubscriptionPlan


class Command(BaseCommand):
    help = "Seed subscription plans in the public schema from environment variables."

    def handle(self, *args, **options):
        pro_monthly = os.environ.get("STRIPE_PRICE_PRO", "").strip()
        agency_monthly = os.environ.get("STRIPE_PRICE_AGENCY", "").strip()
        pro_yearly = os.environ.get("STRIPE_PRICE_PRO_YEARLY", "").strip()
        agency_yearly = os.environ.get("STRIPE_PRICE_AGENCY_YEARLY", "").strip()

        with schema_context("public"):
            plans = [
                {
                    "name": "free",
                    "defaults": {
                        "display_name": "Free",
                        "description": "Basic plan for getting started.",
                        "price_monthly": Decimal("0"),
                        "price_yearly": Decimal("0"),
                        "stripe_price_id_monthly": "",
                        "stripe_price_id_yearly": "",
                        "repurposes_per_month": 2,
                        "brand_voices_limit": 0,
                        "direct_posting": False,
                        "priority_support": False,
                        "is_active": True,
                        "sort_order": 1,
                    },
                },
                {
                    "name": "pro",
                    "defaults": {
                        "display_name": "Pro",
                        "description": "For creators who need more volume and direct posting.",
                        "price_monthly": Decimal("19"),
                        "price_yearly": Decimal("190"),
                        "stripe_price_id_monthly": pro_monthly,
                        "stripe_price_id_yearly": pro_yearly,
                        "repurposes_per_month": 50,
                        "brand_voices_limit": 5,
                        "direct_posting": True,
                        "priority_support": False,
                        "is_active": True,
                        "sort_order": 2,
                    },
                },
                {
                    "name": "agency",
                    "defaults": {
                        "display_name": "Agency",
                        "description": "For teams managing larger publishing volume.",
                        "price_monthly": Decimal("59"),
                        "price_yearly": Decimal("590"),
                        "stripe_price_id_monthly": agency_monthly,
                        "stripe_price_id_yearly": agency_yearly,
                        "repurposes_per_month": -1,
                        "brand_voices_limit": -1,
                        "direct_posting": True,
                        "priority_support": True,
                        "is_active": True,
                        "sort_order": 3,
                    },
                },
            ]

            for plan_data in plans:
                plan, created = SubscriptionPlan.objects.update_or_create(
                    name=plan_data["name"],
                    defaults=plan_data["defaults"],
                )
                action = "Created" if created else "Updated"
                self.stdout.write(f"{action} plan: {plan.name}")

        if not pro_monthly:
            self.stdout.write(self.style.WARNING("STRIPE_PRICE_PRO is not set. Pro monthly checkout will not work."))
        if not agency_monthly:
            self.stdout.write(self.style.WARNING("STRIPE_PRICE_AGENCY is not set. Agency monthly checkout will not work."))

