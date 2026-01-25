from rest_framework import serializers
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from .models import Client, Domain

class ClientSerializer(serializers.ModelSerializer):
    domain_url = serializers.CharField(write_only=True)
    owner_email = serializers.EmailField(write_only=True)
    owner_username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'tenant_type', 'domain_url', 'owner_email', 'owner_username', 'password', 'created_at']

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
        
        # 1. Create Client (Tenant) with explicit schema_name
        client = Client.objects.create(
            schema_name=schema_name,
            **validated_data
        )
        
        # 2. Create Domain
        Domain.objects.create(domain=domain_url, tenant=client, is_primary=True)
        
        # 3. Create Admin User INSIDE the tenant schema
        with schema_context(client.schema_name):
            User = get_user_model()
            user = User.objects.create_user(
                email=owner_email,
                username=owner_username,
                password=password,
                is_staff=True,        # Can access admin
                is_superuser=True,    # Full permissions
                is_tenant_admin=True  # Custom flag if you have it
            )

        # 4. Create UserTenantMap in PUBLIC schema
        from .models import UserTenantMap
        UserTenantMap.objects.create(
            email=owner_email,
            tenant=client
        )
        
        return client
