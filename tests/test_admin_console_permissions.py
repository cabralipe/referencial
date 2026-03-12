import pytest

from core.models import Cliente, Usuario
from curriculum.models import Escola


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


@pytest.mark.django_db
def test_admin_cliente_cria_escola_no_proprio_cliente(api_client, usuario):
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/escolas",
        data={"nome": "Escola Horizonte"},
        format="json",
    )
    assert response.status_code == 201
    escola = Escola.objects.get(pk=response.json()["id"])
    assert escola.cliente_id == usuario.cliente_id


@pytest.mark.django_db
def test_admin_cliente_nao_cria_escola_em_outro_cliente(api_client, cliente, usuario):
    outro_cliente = Cliente.objects.create(nome="Prefeitura D", slug="prefeitura-d")
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/escolas",
        data={"nome": "Escola Externa", "cliente": outro_cliente.id},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_cliente_nao_cria_professor_sem_escola(api_client, usuario):
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/usuarios",
        data={
            "nome": "Professor Sem Escola",
            "email": "prof-sem-escola@teste.com",
            "role": Usuario.Role.PROFESSOR,
            "cliente": usuario.cliente_id,
            "password": "senha123",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "escola" in response.json()


@pytest.mark.django_db
def test_admin_cliente_cria_professor_com_escola_do_mesmo_cliente(api_client, usuario, escola):
    api_client.force_authenticate(usuario)
    response = api_client.post(
        "/api/v1/admin/usuarios",
        data={
            "nome": "Professor Escola",
            "email": "prof-escola@teste.com",
            "role": Usuario.Role.PROFESSOR,
            "cliente": usuario.cliente_id,
            "escola": escola.id,
            "password": "senha123",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["escola"] == escola.id
