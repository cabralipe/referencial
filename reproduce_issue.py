import os
import django
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.threadlocals import set_current_cliente_id
from core.models import Cliente
from consultas.models import ConsultaPublica

def test_visibility():
    # Setup clients
    c1, _ = Cliente.objects.get_or_create(nome="Cliente A", defaults={"slug": "cliente-a"})
    c2, _ = Cliente.objects.get_or_create(nome="Cliente B", defaults={"slug": "cliente-b"})
    
    # Create Consultas
    cp1 = ConsultaPublica.objects.create(
        titulo="Consulta A", 
        cliente=c1, 
        data_publicacao=date.today(),
        ativa=True
    )
    cp2 = ConsultaPublica.objects.create(
        titulo="Consulta B", 
        cliente=c2, 
        data_publicacao=date.today(),
        ativa=True
    )
    
    print(f"Created/Found CP1 (Cliente A): {cp1.id}")
    print(f"Created/Found CP2 (Cliente B): {cp2.id}")
    
    # Test Scope: None (Super Admin)
    set_current_cliente_id(None)
    all_cps = list(ConsultaPublica.objects.values_list('id', flat=True))
    print(f"\nScope None (Super Admin): Found {len(all_cps)} -> {all_cps}")
    
    # Test Scope: Cliente A
    set_current_cliente_id(c1.id)
    c1_cps = list(ConsultaPublica.objects.values_list('id', flat=True))
    print(f"\nScope Cliente A: Found {len(c1_cps)} -> {c1_cps}")
    if cp2.id in c1_cps:
        print("❌ FAIL: Cliente A can see Cliente B's data!")
    else:
        print("✅ PASS: Cliente A cannot see Cliente B's data.")

    # Test Scope: Cliente B
    set_current_cliente_id(c2.id)
    c2_cps = list(ConsultaPublica.objects.values_list('id', flat=True))
    print(f"\nScope Cliente B: Found {len(c2_cps)} -> {c2_cps}")
    
    # Clean up (Soft Delete)
    # cp1.delete() # Don't delete to avoid messing up manual testing if needed
    # cp2.delete()

if __name__ == "__main__":
    test_visibility()
