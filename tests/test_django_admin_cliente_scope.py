import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from core.models import Cliente, Usuario
from curriculum.models import Escola


def _grant_admin_permissions(user: Usuario) -> None:
    permissions = Permission.objects.filter(content_type__app_label__in=["core", "curriculum"])
    user.user_permissions.set(permissions)


@pytest.mark.django_db
def test_admin_cliente_ve_apenas_proprio_cliente_e_usuarios(django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente A", slug="cliente-a")
    cliente_b = Cliente.objects.create(nome="Cliente B", slug="cliente-b")

    admin_cliente: Usuario = django_user_model.objects.create_user(
        email="admin-a@teste.com",
        password="senha123",
        nome="Admin A",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
        is_staff=True,
    )
    usuario_mesmo_cliente = django_user_model.objects.create_user(
        email="membro-a@teste.com",
        password="senha123",
        nome="Membro A",
        cliente=cliente_a,
        role=Usuario.Role.MEMBRO_GT,
    )
    django_user_model.objects.create_user(
        email="membro-b@teste.com",
        password="senha123",
        nome="Membro B",
        cliente=cliente_b,
        role=Usuario.Role.MEMBRO_GT,
    )
    _grant_admin_permissions(admin_cliente)

    client = Client()
    client.force_login(admin_cliente)

    usuarios_response = client.get(reverse("admin:core_usuario_changelist"))
    assert usuarios_response.status_code == 200
    usuarios_html = usuarios_response.content.decode()
    assert admin_cliente.email in usuarios_html
    assert usuario_mesmo_cliente.email in usuarios_html
    assert "membro-b@teste.com" not in usuarios_html
    assert cliente_a.nome in usuarios_html
    assert cliente_b.nome not in usuarios_html

    clientes_response = client.get(reverse("admin:core_cliente_changelist"))
    assert clientes_response.status_code == 200
    clientes_html = clientes_response.content.decode()
    assert cliente_a.nome in clientes_html
    assert cliente_b.nome not in clientes_html


@pytest.mark.django_db
def test_admin_cliente_form_usuario_oculta_cliente_e_filtra_escolas(django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente Escola A", slug="cliente-escola-a")
    cliente_b = Cliente.objects.create(nome="Cliente Escola B", slug="cliente-escola-b")
    escola_a = Escola.objects.create(cliente=cliente_a, nome="Escola A")
    escola_b = Escola.objects.create(cliente=cliente_b, nome="Escola B")

    admin_cliente: Usuario = django_user_model.objects.create_user(
        email="admin-escola@teste.com",
        password="senha123",
        nome="Admin Escola",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
        is_staff=True,
    )
    _grant_admin_permissions(admin_cliente)

    client = Client()
    client.force_login(admin_cliente)

    response = client.get(reverse("admin:core_usuario_add"))
    assert response.status_code == 200

    form = response.context["adminform"].form
    assert "cliente" not in form.fields
    assert list(form.fields["escola"].queryset.values_list("id", flat=True)) == [escola_a.id]
    assert escola_b.id not in form.fields["escola"].queryset.values_list("id", flat=True)


@pytest.mark.django_db
def test_admin_cliente_consegue_criar_usuario_sem_campo_cliente(django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente Admin", slug="cliente-admin")
    escola_a = Escola.objects.create(cliente=cliente_a, nome="Escola Admin")

    admin_cliente: Usuario = django_user_model.objects.create_user(
        email="admin-criador@teste.com",
        password="senha123",
        nome="Admin Criador",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
        is_staff=True,
    )
    _grant_admin_permissions(admin_cliente)

    client = Client()
    client.force_login(admin_cliente)

    response = client.post(
        reverse("admin:core_usuario_add"),
        data={
            "email": "novo-usuario@teste.com",
            "nome": "Novo Usuario",
            "escola": str(escola_a.id),
            "role": Usuario.Role.MEMBRO_GT,
            "password1": "Senha123forte!",
            "password2": "Senha123forte!",
            "is_active": "on",
            "_save": "Salvar",
        },
    )

    assert response.status_code == 302
    usuario = django_user_model.objects.get(email="novo-usuario@teste.com")
    assert usuario.cliente_id == cliente_a.id
    assert usuario.escola_id == escola_a.id
