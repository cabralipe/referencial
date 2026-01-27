import os
import sys
import django
from django.urls import resolve

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from config.views import serve_frontend

def test_urls():
    print("Testing URL resolution...")
    
    # Test cases: (path, should_be_frontend)
    test_cases = [
        ("/admin/mural", True),
        ("/admin/console", True),
        ("/admin/trilhas", True),
        ("/admin/ppp", True),
        ("/admin/login/", False), # Standard Django Admin
        ("/admin/", False),       # Standard Django Admin
    ]
    
    failed = False
    
    for path, should_be_frontend in test_cases:
        try:
            resolver_match = resolve(path)
            is_frontend = resolver_match.func == serve_frontend
            
            status = "OK" if is_frontend == should_be_frontend else "FAIL"
            if status == "FAIL":
                failed = True
                
            expected = "serve_frontend" if should_be_frontend else "not serve_frontend"
            actual = "serve_frontend" if is_frontend else resolver_match.func.__name__
            
            print(f"[{status}] {path} -> {actual} (Expected: {expected})")
            
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
            failed = True
            
    if failed:
        print("\nVerification FAILED.")
        sys.exit(1)
    else:
        print("\nVerification SUCCESS.")
        sys.exit(0)

if __name__ == "__main__":
    test_urls()
