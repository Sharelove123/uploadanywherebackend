from django.core.management.base import BaseCommand
from apps.payments.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'List subscription plans'

    def handle(self, *args, **options):
        plans = SubscriptionPlan.objects.all()
        if not plans:
            self.stdout.write("No plans found in database.")
            return

        self.stdout.write("ID | Name | Display Name")
        self.stdout.write("-" * 30)
        for p in plans:
            self.stdout.write(f"{p.id} | {p.name} | {p.display_name}")
