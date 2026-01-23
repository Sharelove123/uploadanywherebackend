import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Test imports
try:
    from apps.users.serializers import UserProfileSerializer
    print("UserProfileSerializer imported OK")
except Exception as e:
    print(f"Error importing UserProfileSerializer: {e}")

try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    print("JWTAuthentication imported OK")
except Exception as e:
    print(f"Error importing JWTAuthentication: {e}")

try:
    from dj_rest_auth.views import LoginView
    print("dj_rest_auth LoginView imported OK")
except Exception as e:
    print(f"Error importing dj_rest_auth LoginView: {e}")

# Test the API view
try:
    from config.urls import api_root
    print("api_root imported OK")
except Exception as e:
    print(f"Error importing api_root: {e}")

print("\nAll imports successful!")
