import pytest

from core.models import Cliente, Usuario


def test_admin_cliente_nao_cria_super_admin(api_client, cliente, usuario):
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/usuarios",
        data={
            "nome": "Root",
            "email": "root@teste.com",
            "role": Usuario.Role.SUPER_ADMIN,
            "cliente": cliente.id,
            "password": "senha123",
        },
        format="json",
    )
    assert response.status_code == 403


def test_admin_cliente_nao_altera_cliente(api_client, cliente, usuario):
    outro_cliente = Cliente.objects.create(nome="Prefeitura B", slug="prefeitura-b")
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/usuarios",
        data={
            "nome": "Outro",
            "email": "outro@teste.com",
            "role": Usuario.Role.MEMBRO_GT,
            "cliente": outro_cliente.id,
            "password": "senha123",
        },
        format="json",
    )
    assert response.status_code == 403


def test_super_admin_respeita_x_cliente_id(api_client, cliente, django_user_model):
    super_admin = django_user_model.objects.create_user(
        email="super@teste.com",
        password="senha123",
        nome="Super",
        cliente=None,
        role=Usuario.Role.SUPER_ADMIN,
    )
    cliente_b = Cliente.objects.create(nome="Prefeitura C", slug="prefeitura-c")
    django_user_model.objects.create_user(
        email="usera@teste.com",
        password="senha123",
        nome="User A",
        cliente=cliente,
        role=Usuario.Role.MEMBRO_GT,
    )
    django_user_model.objects.create_user(
        email="userb@teste.com",
        password="senha123",
        nome="User B",
        cliente=cliente_b,
        role=Usuario.Role.MEMBRO_GT,
    )
    api_client.force_authenticate(super_admin)
    response = api_client.get("/api/v1/admin/usuarios", HTTP_X_CLIENTE_ID=str(cliente.id))
    assert response.status_code == 200
    payload = response.json()
    results = payload.get("results", payload)
    assert all(item["cliente"] == cliente.id for item in results)
