#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Migrate public schema
python manage.py migrate_schemas --shared

# Migrate tenant schemas
python manage.py migrate_schemas --tenant
