import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Usuario, ClienteTema


@pytest.fixture
def cliente_usuario(cliente, django_user_model):
    return django_user_model.objects.create_user(
        email="cliente@teste.com",
        password="senha123",
        nome="Cliente Curioso",
        cliente=cliente,
        role=Usuario.Role.MEMBRO_GT,
    )


@pytest.mark.django_db
def test_cliente_envia_mensagem_e_recebe_resposta_do_meb(cliente_usuario):
    client = APIClient()
    client.force_authenticate(cliente_usuario)

    response = client.post("/api/v1/meb/mensagens", {"conteudo": "Esqueci minha senha de login"})
    assert response.status_code == 201
    data = response.json()
    assert data["origem"] == "cliente"
    assert data["autor"] == cliente_usuario.id

    mensagens = client.get("/api/v1/meb/mensagens").json()
    assert len(mensagens) >= 2
    assert any(msg["origem"] == "meb" for msg in mensagens)
    assert any("senha" in msg["conteudo"].lower() for msg in mensagens if msg["origem"] == "meb")


@pytest.mark.django_db
def test_admin_consegue_ver_threads_e_responder(cliente_usuario, usuario):
    cliente_client = APIClient()
    cliente_client.force_authenticate(cliente_usuario)
    cliente_client.post("/api/v1/meb/mensagens", {"conteudo": "Preciso enviar as tarefas ainda hoje."})

    admin_client = APIClient()
    admin_client.force_authenticate(usuario)

    threads = admin_client.get("/api/v1/meb/threads").json()
    assert any(thread["usuario"] == cliente_usuario.id for thread in threads)

    resposta = admin_client.post(
        "/api/v1/meb/mensagens",
        {"usuario": cliente_usuario.id, "conteudo": "Tudo certo, já encaminhei para o GT."},
    )
    assert resposta.status_code == 201
    assert resposta.json()["origem"] == "admin"

    mensagens = admin_client.get(f"/api/v1/meb/mensagens?usuario_id={cliente_usuario.id}").json()
    assert any(msg["origem"] == "admin" for msg in mensagens)


@pytest.mark.django_db
def test_cliente_nao_consegue_mandar_mensagem_em_nome_de_outro(cliente_usuario, membro_gt):
    client = APIClient()
    client.force_authenticate(cliente_usuario)

    resposta = client.post(
        "/api/v1/meb/mensagens",
        {"usuario": membro_gt.id, "conteudo": "Tentando enviar como outra pessoa"},
    )
    assert resposta.status_code == 400
    body = resposta.json()
    assert "usuario" in body


@pytest.mark.django_db
def test_admin_envia_avatar_do_meb(cliente, usuario):
    client = APIClient()
    client.force_authenticate(usuario)
    arquivo = SimpleUploadedFile("avatar.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00", content_type="image/png")
    response = client.post("/api/v1/meb/avatar", {"avatar": arquivo})
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    tema = ClienteTema.objects.get(cliente=cliente)
    assert tema.meb_avatar_url == data["url"]


@pytest.mark.django_db
def test_membro_nao_envia_avatar(cliente_usuario):
    client = APIClient()
    client.force_authenticate(cliente_usuario)
    arquivo = SimpleUploadedFile("avatar.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00", content_type="image/png")
    response = client.post("/api/v1/meb/avatar", {"avatar": arquivo})
    assert response.status_code == 403
