#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Auto-create superuser from environment variables (if not exists)
python manage.py createsuperuser --noinput || true

# NOTE: Database migrations should NOT run in the build step on Render/Heroku
# because the database is often not accessible during the build phase.
# We will run them in the Start Command or entrypoint.
