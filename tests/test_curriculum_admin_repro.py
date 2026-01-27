import os
import sys
import django
from django.contrib.admin.helpers import ActionForm

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from curriculum.admin import BroadcastMessageForm

def test_action_form_has_action_field():
    print("Testing (Curriculum) BroadcastMessageForm structure...")
    
    # Try to instantiate the form
    form = BroadcastMessageForm()
    
    # Check if 'action' field is present
    if 'action' in form.fields:
        print("[OK] 'action' field is present in BroadcastMessageForm.")
    else:
        print("[FAIL] 'action' field is MISSING in BroadcastMessageForm.")
        return False
            
    return True

if __name__ == "__main__":
    if not test_action_form_has_action_field():
        sys.exit(1)
    sys.exit(0)
