#!/usr/bin/env python
"""Reset admin password script"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    u = User.objects.get(username='admin')
    u.set_password('admin123')
    u.save()
    print('Password reset successfully!')
    print('Username: admin')
    print('Password: admin123')
except User.DoesNotExist:
    print('User "admin" does not exist')
