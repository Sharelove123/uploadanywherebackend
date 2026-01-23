import os
import django
from django.conf import settings
import dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Checking .env at: {env_path}")
try:
    with open(env_path, 'r') as f:
        print("First 50 chars of .env:", f.read(50))
except Exception as e:
    print(f"Error reading .env: {e}")

dotenv.load_dotenv(env_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("DATABASE ENGINE:", settings.DATABASES['default']['ENGINE'])
print("DATABASE NAME:", settings.DATABASES['default']['NAME'])
print("DATABASE URL ENV:", os.environ.get('DATABASE_URL'))
