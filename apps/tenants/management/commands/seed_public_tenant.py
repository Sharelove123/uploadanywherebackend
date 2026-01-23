import os
from django.core.management.base import BaseCommand
from apps.tenants.models import Client, Domain


class Command(BaseCommand):
    help = 'Seeds the public tenant and its domains if they do not exist.'

    def handle(self, *args, **options):
        # Check if public tenant already exists
        public_tenant = Client.objects.filter(schema_name='public').first()
        
        if not public_tenant:
            self.stdout.write('Creating public tenant...')
            public_tenant = Client.objects.create(
                schema_name='public',
                name='Public',
                tenant_type='company',
            )
            self.stdout.write(self.style.SUCCESS(f'Created public tenant: {public_tenant}'))
        else:
            self.stdout.write(self.style.WARNING(f'Public tenant already exists: {public_tenant}'))

        # Get the domains to register from environment or use defaults
        # FRONTEND_URL might be https://uploadanywherefrontend.vercel.app
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        # Extract just the domain without protocol
        frontend_domain = frontend_url.replace('https://', '').replace('http://', '').rstrip('/')
        
        # Also get the Render domain (the Host header of API requests)
        # This is usually the actual backend hostname
        render_domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
        
        # Define all domains that should route to public schema
        domains_to_create = [
            'localhost',
            '127.0.0.1',
            frontend_domain,
        ]
        
        if render_domain:
            domains_to_create.append(render_domain)
        
        # Remove empty strings and duplicates
        domains_to_create = list(set(filter(None, domains_to_create)))
        
        for domain_name in domains_to_create:
            domain, created = Domain.objects.get_or_create(
                domain=domain_name,
                defaults={
                    'tenant': public_tenant,
                    'is_primary': domain_name == frontend_domain,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created domain: {domain_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Domain already exists: {domain_name}'))
        
        self.stdout.write(self.style.SUCCESS('Public tenant seeding complete!'))
