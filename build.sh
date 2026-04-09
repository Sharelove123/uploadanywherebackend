#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Run migrations for all tenants (django-tenants)
python manage.py makemigrations --noinput || true
python manage.py migrate_schemas --noinput

# 12. Create Public Tenant if it doesn't exist
python create_tenants.py

# Seed subscription plans in public schema from environment variables
python manage.py seed_subscription_plans

# Make start script executable
chmod +x start_combined.sh

# Auto-create superuser from environment variables (if not exists)
python manage.py createsuperuser --noinput || true
