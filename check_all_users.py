import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Usuario

def check_all_users():
    test_users = [
        "super@test.com",
        "admin@test.com",
        "articulador@test.com",
        "membro@test.com",
        "leitor@test.com"
    ]
    password = "123456"
    
    for email in test_users:
        try:
            user = Usuario.objects.get(email=email)
            is_valid = user.check_password(password)
            print(f"User: {email} | Password '123456' valid: {is_valid}")
            if not is_valid:
                print(f"  -> Resetting password for {email}...")
                user.set_password(password)
                user.save()
                print(f"  -> Password reset.")
        except Usuario.DoesNotExist:
            print(f"User {email} does not exist.")

if __name__ == "__main__":
    check_all_users()
