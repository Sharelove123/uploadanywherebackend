from rest_framework import serializers
from django.db import transaction
from .models import Client, Domain, UserTenantMap
from .tasks import provision_tenant

class ClientSerializer(serializers.ModelSerializer):
    domain_url = serializers.CharField(write_only=True)
    owner_email = serializers.EmailField(write_only=True)
    owner_username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'tenant_type', 'domain_url', 'owner_email', 'owner_username', 'password', 'created_at']

    def validate(self, attrs):
        domain_url = attrs.get('domain_url', '').strip().lower()
        owner_email = attrs.get('owner_email', '').strip().lower()

        import re
        schema_name = domain_url.split('.')[0]
        schema_name = re.sub(r'[^a-z0-9]', '', schema_name.lower())

        errors = {}

        if Domain.objects.filter(domain__iexact=domain_url).exists():
            errors['domain_url'] = 'This subdomain is already registered.'

        if schema_name and Client.objects.filter(schema_name=schema_name).exists():
            errors['domain_url'] = 'This subdomain is already registered.'

        if owner_email and UserTenantMap.objects.filter(email__iexact=owner_email).exists():
            errors['owner_email'] = 'This email is already linked to an existing tenant.'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        domain_url = validated_data.pop('domain_url')
        owner_email = validated_data.pop('owner_email')
        owner_username = validated_data.pop('owner_username')
        password = validated_data.pop('password')
        
        # Generate valid schema_name from domain (e.g., "acme.localhost" -> "acme")
        # Schema names must be lowercase, alphanumeric, no spaces
        import re
        schema_name = domain_url.split('.')[0]  # Get subdomain part
        schema_name = re.sub(r'[^a-z0-9]', '', schema_name.lower())  # Sanitize
        
        if not schema_name or len(schema_name) < 1:
            schema_name = f"tenant_{validated_data.get('name', 'default')[:10].lower().replace(' ', '')}"
        
        # 1. Create Client (Tenant) without provisioning the schema inline.
        client = Client.objects.create(
            schema_name=schema_name,
            **validated_data
        )
        
        # 2. Create Domain
        Domain.objects.create(domain=domain_url, tenant=client, is_primary=True)
        
        # 3. Create UserTenantMap in PUBLIC schema
        UserTenantMap.objects.create(
            email=owner_email,
            tenant=client
        )

        # 4. Provision the tenant schema and admin user asynchronously.
        transaction.on_commit(
            lambda: provision_tenant.delay(
                client.id,
                owner_email,
                owner_username,
                password,
            )
        )
        
        return client
