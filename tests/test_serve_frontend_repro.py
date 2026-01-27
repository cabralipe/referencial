import os
import sys
import django
from django.test import RequestFactory
from django.urls import resolve

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from config.views import serve_frontend

def test_serve_frontend_args():
    print("Testing serve_frontend argument handling...")
    
    factory = RequestFactory()
    request = factory.get('/admin/mural')
    
    # Mimic what URL resolver does when it finds a match with arguments
    # It calls view(request, *args, **kwargs)
    
    captured_arg = "mural" # from r"^admin/(mural|console|trilhas|ppp)"
    
    try:
        response = serve_frontend(request, captured_arg)
        print("[OK] serve_frontend accepted the extra argument.")
    except TypeError as e:
        print(f"[FAIL] serve_frontend raised TypeError: {e}")
        return False
            
    return True

if __name__ == "__main__":
    if not test_serve_frontend_args():
        sys.exit(1)
    sys.exit(0)
