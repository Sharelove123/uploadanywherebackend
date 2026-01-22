import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import CustomUser
u = CustomUser.objects.get(username='admin')
u.set_password('admin123')
u.save()
print('Password set successfully!')
