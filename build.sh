#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Run migrations (Render connects DB during build if using PostgreSQL)
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput

# Auto-create superuser from environment variables (if not exists)
python manage.py createsuperuser --noinput || true
