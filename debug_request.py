
import os
import django
from django.conf import settings
from django.test import RequestFactory, Client

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Use Client which includes Middleware processing
client = Client()

print("\n--- Testing API Root with Client ---")
try:
    response = client.get('/api/')
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Content: {response.content.decode()}")
except Exception as e:
    import traceback
    traceback.print_exc()

print("\n--- Testing Login with Client ---")
try:
    response = client.post('/api/auth/login/', {'username': 'admin', 'password': 'admin123'})
    if response.status_code != 200:
        print(f"Status: {response.status_code}")
        with open('error.html', 'wb') as f:
            f.write(response.content)
        print("Error content saved to error.html")
except Exception as e:
    import traceback
    traceback.print_exc()
