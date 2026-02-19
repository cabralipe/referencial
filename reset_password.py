import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Usuario

def reset_password():
    email = "admin@test.com"
    password = "123456"
    
    try:
        user = Usuario.objects.get(email=email)
        user.set_password(password)
        user.save()
        print(f"Password for {email} reset to {password}")
    except Usuario.DoesNotExist:
        print(f"User {email} does not exist")

if __name__ == "__main__":
    reset_password()
