
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import dotenv
dotenv.load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    username = 'admin'
    email = 'admin@example.com'
    password = 'admin'
    
    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser: {username}")
        User.objects.create_superuser(username, email, password)
        print(f"Superuser created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
    else:
        print(f"Superuser '{username}' already exists.")
        # Optional: Reset password if it exists but user forgot
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
        print(f"Password reset to '{password}' for user '{username}'.")

if __name__ == '__main__':
    create_admin()
