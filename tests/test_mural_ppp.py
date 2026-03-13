import pytest

from core.models import Usuario
from curriculum.models import PPP


@pytest.mark.django_db
def test_membro_gt_nao_pode_criar_mural(api_client, cliente, membro_gt):
    membro_gt.cliente = cliente
    membro_gt.save(update_fields=["cliente"])
    api_client.force_authenticate(membro_gt)
    resp = api_client.post(
        "/api/v1/mural",
        {"titulo": "Aviso", "conteudo_html": "<p>Teste</p>"},
        format="json",
    )
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_ppp_e_criado_para_escola_do_diretor(api_client, cliente, escola, django_user_model):
    diretor = django_user_model.objects.create_user(
        email="diretor@teste.com",
        password="senha123",
        nome="Diretora Escolar",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.DIRETOR,
    )
    api_client.force_authenticate(diretor)

    resp = api_client.get("/api/v1/ppp")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["escola"] == escola.id
    assert payload["escola_nome"] == escola.nome
    assert payload["status"] == PPP.Status.EM_ELABORACAO
    assert payload["can_edit"] is True


@pytest.mark.django_db
def test_redator_comenta_ppp_da_escola_e_diretor_visualiza(api_client, cliente, escola, django_user_model):
    diretor = django_user_model.objects.create_user(
        email="diretor.ppp@teste.com",
        password="senha123",
        nome="Diretora PPP",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.DIRETOR,
    )
    redator = django_user_model.objects.create_user(
        email="redator.ppp@teste.com",
        password="senha123",
        nome="Redator PPP",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.ARTICULADOR,
    )

    api_client.force_authenticate(diretor)
    ppp_resp = api_client.get("/api/v1/ppp")
    ppp_id = ppp_resp.json()["id"]

    api_client.force_authenticate(redator)
    create_resp = api_client.post(
        "/api/v1/comentarios",
        {
            "alvo_tipo": "ppp",
            "alvo_id": ppp_id,
            "conteudo_html": "<p>Inserir referências do diagnóstico institucional.</p>",
            "anchor_json": {"local": "Introdução"},
        },
        format="json",
    )

    assert create_resp.status_code == 201

    api_client.force_authenticate(diretor)
    list_resp = api_client.get(f"/api/v1/comentarios?alvo_tipo=ppp&alvo_id={ppp_id}")

    assert list_resp.status_code == 200
    results = list_resp.json()["results"]
    assert len(results) == 1
    assert results[0]["alvo_preview"]["type"] == "ppp"
    assert results[0]["alvo_preview"]["escola_nome"] == escola.nome


@pytest.mark.django_db
def test_apenas_direcao_ou_coordenacao_concluem_ppp(api_client, cliente, escola, django_user_model):
    diretor = django_user_model.objects.create_user(
        email="diretor.final@teste.com",
        password="senha123",
        nome="Diretora Final",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.DIRETOR,
    )
    redator = django_user_model.objects.create_user(
        email="redator.final@teste.com",
        password="senha123",
        nome="Redator Final",
        cliente=cliente,
        escola=escola,
        role=Usuario.Role.ARTICULADOR,
    )

    api_client.force_authenticate(diretor)
    ppp_resp = api_client.get("/api/v1/ppp")
    payload = ppp_resp.json()
    ppp_id = payload["id"]
    etag = payload["etag"]

    api_client.force_authenticate(redator)
    save_resp = api_client.patch(
        "/api/v1/ppp/conteudo",
        {
            "conteudo_html": "<p>Texto consolidado do PPP.</p>",
            "titulo": "PPP Escola Base",
        },
        format="json",
        HTTP_IF_MATCH=etag,
    )
    assert save_resp.status_code == 200

    redator_etag = save_resp.json()["etag"]
    conclude_denied = api_client.post("/api/v1/ppp/concluir", format="json", HTTP_IF_MATCH=redator_etag)
    assert conclude_denied.status_code == 403

    api_client.force_authenticate(diretor)
    refreshed = api_client.get("/api/v1/ppp")
    conclude_resp = api_client.post("/api/v1/ppp/concluir", format="json", HTTP_IF_MATCH=refreshed.json()["etag"])
    assert conclude_resp.status_code == 200
    assert conclude_resp.json()["status"] == PPP.Status.CONCLUIDO

    pdf_resp = api_client.get("/api/v1/ppp/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp["Content-Type"] == "application/pdf"

    assert PPP.objects.get(pk=ppp_id).status == PPP.Status.CONCLUIDO
