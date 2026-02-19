import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Usuario
from django.contrib.auth import authenticate

def check_user():
    email = "admin@test.com"
    password = "123456"
    
    try:
        user = Usuario.objects.get(email=email)
        print(f"User found: {user.email}")
        print(f"Is active: {user.is_active}")
        print(f"Password correct (check_password): {user.check_password(password)}")
        
        auth_user = authenticate(username=email, password=password)
        print(f"Authenticate result: {auth_user}")
        
    except Usuario.DoesNotExist:
        print(f"User {email} does not exist")

if __name__ == "__main__":
    check_user()
