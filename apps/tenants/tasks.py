import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context

from .models import Client

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def provision_tenant(self, client_id, owner_email, owner_username, password):
    client = Client.objects.get(id=client_id)

    with connection.cursor() as cursor:
        cursor.execute("select schema_name from information_schema.schemata")
        existing_schemas = {row[0] for row in cursor.fetchall()}
    if client.schema_name not in existing_schemas:
        client.create_schema(check_if_exists=True, verbosity=1)

    with schema_context(client.schema_name):
        User = get_user_model()
        User.objects.update_or_create(
            email=owner_email,
            defaults={
                "username": owner_username,
                "is_staff": True,
                "is_superuser": True,
                "is_tenant_admin": True,
            },
        )
        user = User.objects.get(email=owner_email)
        user.set_password(password)
        user.save(update_fields=["password", "username", "is_staff", "is_superuser", "is_tenant_admin"])

    logger.info("Provisioned tenant schema and admin user for client_id=%s schema=%s", client_id, client.schema_name)
