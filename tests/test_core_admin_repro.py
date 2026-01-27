import os
import sys
import django
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.admin import UsuarioAdmin, BroadcastMessageForm
from core.models import Usuario

class MockRequest:
    POST = {}
    GET = {}

def test_action_form_has_action_field():
    print("Testing BroadcastMessageForm structure...")
    
    # Try to instantiate the form
    form = BroadcastMessageForm()
    
    # Check if 'action' field is present
    if 'action' in form.fields:
        print("[OK] 'action' field is present in BroadcastMessageForm.")
    else:
        print("[FAIL] 'action' field is MISSING in BroadcastMessageForm.")
        # This mimics what happens in django admin
        try:
             # This is what Django does: action_form.fields['action'].choices = ...
             _ = form.fields['action']
        except KeyError as e:
            print(f"       Reproduced expected error: KeyError: {e}")
            return False
            
    return True

if __name__ == "__main__":
    if not test_action_form_has_action_field():
        sys.exit(1)
    sys.exit(0)
