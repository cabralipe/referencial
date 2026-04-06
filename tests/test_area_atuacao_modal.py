import pytest

from core.models import TipoUsuarioCadastro, Usuario
from curriculum.models import Escola


@pytest.mark.django_db
def test_area_atuacao_lista_tipos_em_ordem_alfabetica_e_exige_confirmacao(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Centro")
    usuario = Usuario.objects.create_user(
        email="professor-base@teste.com",
        password="senha123",
        nome="Professor Base",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.PROFESSOR,
    )
    TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Zeladoria",
        slug="zeladoria",
        role_interno=Usuario.Role.DIRETOR,
        ativo=True,
    )
    TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Articulação Pedagógica",
        slug="articulacao-pedagogica",
        role_interno=Usuario.Role.DIRETOR,
        ativo=True,
    )
    TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Biblioteca",
        slug="biblioteca",
        role_interno=Usuario.Role.DIRETOR,
        ativo=False,
    )

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/auth/area-atuacao")

    assert response.status_code == 200
    payload = response.json()
    assert payload["required"] is True
    assert [item["nome"] for item in payload["tipos"]] == [
        "Articulação Pedagógica",
        "Zeladoria",
    ]


@pytest.mark.django_db
def test_area_atuacao_confirma_tipo_e_nao_exibe_novamente(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Norte")
    usuario = Usuario.objects.create_user(
        email="diretor-base@teste.com",
        password="senha123",
        nome="Diretor Base",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.DIRETOR,
    )
    tipo = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Conselheiro da Educação",
        slug="conselheiro-da-educacao",
        role_interno=Usuario.Role.DIRETOR,
        ativo=True,
    )

    api_client.force_authenticate(usuario)
    post_response = api_client.post(
        "/api/v1/auth/area-atuacao",
        {"tipo_cadastro_id": tipo.id},
        format="json",
    )

    assert post_response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.tipo_cadastro_id == tipo.id
    assert usuario.area_atuacao_confirmada_em is not None
    assert usuario.role == Usuario.Role.DIRETOR

    get_response = api_client.get("/api/v1/auth/area-atuacao")
    assert get_response.status_code == 200
    assert get_response.json()["required"] is False


@pytest.mark.django_db
def test_usuario_criado_com_tipo_cadastro_nao_fica_pendente(api_client, cliente):
    escola = Escola.objects.create(cliente=cliente, nome="Escola Sul")
    tipo = TipoUsuarioCadastro.objects.create(
        cliente=cliente,
        nome="Professor Regente",
        slug="professor-regente",
        role_interno=Usuario.Role.PROFESSOR,
        ativo=True,
    )
    usuario = Usuario.objects.create_user(
        email="professor-regente@teste.com",
        password="senha123",
        nome="Professor Regente",
        cliente=cliente,
        escola=escola,
        tipo_cadastro=tipo,
        role=Usuario.Role.PROFESSOR,
    )

    api_client.force_authenticate(usuario)
    response = api_client.get("/api/v1/auth/area-atuacao")

    assert response.status_code == 200
    assert response.json()["required"] is False
