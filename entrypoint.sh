#!/usr/bin/env bash
set -o errexit

# Migrate public schema
python manage.py migrate_schemas --shared

# Migrate tenant schemas
python manage.py migrate_schemas --tenant

# Seed the public tenant with domains (optional, safe to re-run?)
python manage.py seed_public_tenant || true

# Start Gunicorn
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
