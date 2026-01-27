import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from core.models import Usuario
from api.v1.views import AuthMeView

def test_auth_me_superuser():
    print("Testing AuthMeView for superuser...")
    
    # Create a superuser
    email = "super_test@test.com"
    password = "password123"
    
    if Usuario.objects.filter(email=email).exists():
        user = Usuario.objects.get(email=email)
    else:
        user = Usuario.objects.create_superuser(email=email, password=password)
        
    print(f"User created/retrieved: {user.email}, Role: {user.role}, Cliente: {user.cliente}")

    factory = APIRequestFactory()
    request = factory.get('/api/v1/auth/me')
    force_authenticate(request, user=user)
    
    view = AuthMeView.as_view()
    
    try:
        response = view(request)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            print("[OK] Superuser accessed AuthMeView successfully.")
            return True
        else:
            print(f"[FAIL] Superuser denied. Data: {response.data}")
            return False
    except Exception as e:
        print(f"[FAIL] Exception during view execution: {e}")
        return False

if __name__ == "__main__":
    if not test_auth_me_superuser():
        sys.exit(1)
    sys.exit(0)
