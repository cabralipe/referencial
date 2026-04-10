import pytest

from core.models import Cliente, Usuario


@pytest.mark.django_db
def test_auth_me_permuta_escopo_para_cliente_permitido(api_client, django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente A", slug="multi-cliente-a")
    cliente_b = Cliente.objects.create(nome="Cliente B", slug="multi-cliente-b")
    usuario = django_user_model.objects.create_user(
        email="multicliente@teste.com",
        password="senha123",
        nome="Usuario Multi",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    usuario.clientes.add(cliente_b)

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/auth/me", HTTP_X_CLIENTE_ID=str(cliente_b.id))

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["cliente_id"] == cliente_b.id
    assert payload["cliente"]["cliente"]["id"] == cliente_b.id
    assert {item["id"] for item in payload["user"]["clientes"]} == {cliente_a.id, cliente_b.id}


@pytest.mark.django_db
def test_scope_header_ignora_cliente_nao_permitido(api_client, django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente Base", slug="scope-base")
    cliente_b = Cliente.objects.create(nome="Cliente Permitido", slug="scope-permitido")
    cliente_c = Cliente.objects.create(nome="Cliente Bloqueado", slug="scope-bloqueado")
    usuario = django_user_model.objects.create_user(
        email="scope@teste.com",
        password="senha123",
        nome="Usuario Scope",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    usuario.clientes.add(cliente_b)

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/cliente/me", HTTP_X_CLIENTE_ID=str(cliente_c.id))

    assert response.status_code == 200
    assert response.json()["cliente"]["id"] == cliente_a.id


@pytest.mark.django_db
def test_admin_console_lista_usuarios_por_cliente_permitido(api_client, django_user_model):
    cliente_a = Cliente.objects.create(nome="Cliente Lista A", slug="lista-cliente-a")
    cliente_b = Cliente.objects.create(nome="Cliente Lista B", slug="lista-cliente-b")

    admin = django_user_model.objects.create_user(
        email="admin-lista@teste.com",
        password="senha123",
        nome="Admin Lista",
        cliente=cliente_a,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    admin.clientes.add(cliente_b)

    usuario_cliente_b = django_user_model.objects.create_user(
        email="usuario-b@teste.com",
        password="senha123",
        nome="Usuario B",
        cliente=cliente_b,
        role=Usuario.Role.MEMBRO_GT,
    )

    api_client.force_authenticate(admin)
    response = api_client.get("/api/v1/admin/usuarios", HTTP_X_CLIENTE_ID=str(cliente_b.id))

    assert response.status_code == 200
    payload = response.json()
    results = payload.get("results", payload)
    emails = {item["email"] for item in results}
    assert admin.email in emails
    assert usuario_cliente_b.email in emails
