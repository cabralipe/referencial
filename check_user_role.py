
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

try:
    user = Usuario.objects.get(email="admin@test.com")
    print(f"User found: {user.email}")
    print(f"Current Role: {user.role}")
    print(f"Client: {user.cliente}")
    print(f"Is Superuser: {user.is_superuser}")
    print(f"Is Staff: {user.is_staff}")
except Usuario.DoesNotExist:
    print("User 'admin@test.com' not found.")
except Exception as e:
    print(f"Error: {e}")
