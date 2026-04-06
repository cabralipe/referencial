import pytest

from core.models import TipoUsuarioCadastro, Usuario
from curriculum.models import Escola, PPP


@pytest.mark.django_db
def test_public_cadastro_data_lista_apenas_tipos_visiveis(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Centro")
    tipo_visivel = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Diretor",
        slug="diretor",
        role_interno=Usuario.Role.DIRETOR,
        acesso_ppp=TipoUsuarioCadastro.AcessoPPP.EDITAR,
        exibir_no_cadastro=True,
        ativo=True,
        ordem_exibicao=10,
    )
    TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Professor interno",
        slug="professor-interno",
        role_interno=Usuario.Role.PROFESSOR,
        acesso_ppp=TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
        exibir_no_cadastro=False,
        ativo=True,
        ordem_exibicao=20,
    )

    response = api_client.get("/api/v1/public/cadastro-data")

    assert response.status_code == 200
    payload = response.json()
    assert payload["clientes"][0]["id"] == cliente.id
    assert payload["escolas"][0]["id"] == escola.id
    assert payload["tipos_cadastro"] == [
        {
            "id": tipo_visivel.id,
            "nome": "Diretor",
            "cliente_id": cliente.id,
        }
    ]


@pytest.mark.django_db
def test_public_cadastro_cria_usuario_a_partir_do_tipo(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Sul")
    tipo = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Professor - Anos Iniciais",
        slug="professor-anos-iniciais",
        role_interno=Usuario.Role.PROFESSOR,
        seguimento=Usuario.Seguimento.PROFESSOR_ANOS_INICIAIS,
        acesso_ppp=TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
        exibir_no_cadastro=True,
        ativo=True,
        ordem_exibicao=10,
    )

    response = api_client.post(
        "/api/v1/public/cadastro",
        {
            "nome": "Professora Nova",
            "email": "nova@teste.com",
            "password": "senha123",
            "tipo_cadastro_id": tipo.id,
            "cliente_id": cliente.id,
            "escola_id": escola.id,
        },
        format="json",
    )

    assert response.status_code == 201
    usuario = Usuario.objects.get(email="nova@teste.com")
    assert usuario.tipo_cadastro_id == tipo.id
    assert usuario.role == Usuario.Role.PROFESSOR
    assert usuario.seguimento == Usuario.Seguimento.PROFESSOR_ANOS_INICIAIS


@pytest.mark.django_db
def test_professor_com_tipo_editavel_pode_editar_ppp(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Norte")
    tipo = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Professor Editor",
        slug="professor-editor",
        role_interno=Usuario.Role.PROFESSOR,
        acesso_ppp=TipoUsuarioCadastro.AcessoPPP.EDITAR,
        exibir_no_cadastro=True,
        ativo=True,
        ordem_exibicao=10,
    )
    usuario = Usuario.objects.create_user(
        email="editor@teste.com",
        password="senha123",
        nome="Professor Editor",
        cliente=cliente,
        escola=escola,
        tipo_cadastro=tipo,
        role=Usuario.Role.PROFESSOR,
    )

    api_client.force_authenticate(usuario)
    response = api_client.patch(
        "/api/v1/ppp/conteudo",
        {"titulo": "PPP Escola Norte", "conteudo_html": "<p>Texto</p>"},
        format="json",
        HTTP_X_CLIENTE_ID=str(cliente.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["can_edit"] is True
    assert payload["titulo"] == "PPP Escola Norte"


@pytest.mark.django_db
def test_professor_com_tipo_visualizacao_recebe_ppp_somente_para_leitura(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Leste")
    tipo = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Professor Leitor",
        slug="professor-leitor",
        role_interno=Usuario.Role.PROFESSOR,
        acesso_ppp=TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
        exibir_no_cadastro=True,
        ativo=True,
        ordem_exibicao=10,
    )
    usuario = Usuario.objects.create_user(
        email="leitor-ppp@teste.com",
        password="senha123",
        nome="Professor Leitor",
        cliente=cliente,
        escola=escola,
        tipo_cadastro=tipo,
        role=Usuario.Role.PROFESSOR,
    )
    PPP.objects.create(
        cliente=cliente,
        escola=escola,
        titulo="PPP Concluido",
        conteudo_html="<p>Final</p>",
        status=PPP.Status.CONCLUIDO,
        concluido_por=usuario,
        ultima_edicao_por=usuario,
    )

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/ppp", HTTP_X_CLIENTE_ID=str(cliente.id))

    assert response.status_code == 200
    payload = response.json()
    assert payload["can_edit"] is False
    assert payload["can_comment"] is False
    assert payload["status"] == PPP.Status.CONCLUIDO
