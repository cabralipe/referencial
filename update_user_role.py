
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

try:
    user = Usuario.objects.get(email="admin@test.com")
    
    # Update role
    user.role = Usuario.Role.ADMIN_CLIENTE
    user.is_superuser = False
    user.is_staff = False  # Assuming regular admin_clinet doesn't need django admin access
    user.save()
    
    print(f"User updated: {user.email}")
    print(f"New Role: {user.role}")
    print(f"Is Superuser: {user.is_superuser}")
    print(f"Is Staff: {user.is_staff}")
    
except Usuario.DoesNotExist:
    print("User 'admin@test.com' not found.")
except Exception as e:
    print(f"Error: {e}")
