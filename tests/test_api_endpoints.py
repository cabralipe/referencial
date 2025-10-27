import pytest
from curriculum.models import GT, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from workshop.models import Quadro


@pytest.mark.django_db
def test_resposta_crud_flow(auth_client, gt, pergunta):
    create_resp = auth_client.post(
        "/api/v1/respostas",
        {"gt": gt.id, "pergunta": pergunta.id, "conteudo_html": "<p>Primeira</p>"},
        format="json",
    )
    assert create_resp.status_code == 201
    resposta_id = create_resp.json()["id"]

    update_resp = auth_client.put(
        f"/api/v1/respostas/{resposta_id}",
        {"gt": gt.id, "pergunta": pergunta.id, "conteudo_html": "<p>Atualizada</p>"},
        format="json",
        HTTP_IF_MATCH=create_resp["ETag"],
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["version"] == 2

    list_resp = auth_client.get("/api/v1/respostas")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1

    delete_resp = auth_client.delete(f"/api/v1/respostas/{resposta_id}")
    assert delete_resp.status_code == 204

    after_delete = auth_client.get("/api/v1/respostas")
    assert after_delete.json()["count"] == 0


@pytest.mark.django_db
def test_gt_endpoint_lists_for_admin(auth_client, cliente):
    GT.objects.create(cliente=cliente, nome="GT Norte", etapa="I")
    GT.objects.create(cliente=cliente, nome="GT Sul", etapa="II")

    response = auth_client.get("/api/v1/gts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    nomes = {item["nome"] for item in payload["results"]}
    assert {"GT Norte", "GT Sul"} == nomes


@pytest.mark.django_db
def test_gt_endpoint_filters_by_membership(api_client, cliente, membro_gt):
    gt_visivel = GT.objects.create(cliente=cliente, nome="GT Visível", etapa="I")
    GT.objects.create(cliente=cliente, nome="GT Oculto", etapa="II")
    gt_visivel.membros.add(membro_gt)

    api_client.force_authenticate(membro_gt)
    response = api_client.get("/api/v1/gts")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["nome"] == gt_visivel.nome


@pytest.mark.django_db
def test_formulario_endpoints(auth_client, cliente):
    formulario = FormularioDinamico.objects.create(cliente=cliente, nome="Inscrição")
    CampoDinamico.objects.create(
        cliente=cliente,
        formulario=formulario,
        chave="modalidade",
        tipo=CampoDinamico.Tipo.SELECT,
        config_json={"choices": ["presencial", "remoto"]},
        ordem=1,
    )

    campos = auth_client.get(f"/api/v1/formularios/{formulario.id}/campos")
    assert campos.status_code == 200
    assert campos.json()[0]["chave"] == "modalidade"

    resposta = auth_client.post(
        f"/api/v1/formularios/{formulario.id}/respostas",
        {
            "campo": formulario.campos.first().id,
            "valor_texto": "presencial",
            "owner_type": "resposta",
            "owner_id": "dummy",
        },
        format="json",
    )
    assert resposta.status_code == 201


@pytest.mark.django_db
def test_formulario_respostas_upsert(auth_client, cliente):
    formulario = FormularioDinamico.objects.create(cliente=cliente, nome="Inscrição")
    campo = CampoDinamico.objects.create(
        cliente=cliente,
        formulario=formulario,
        chave="modalidade",
        tipo=CampoDinamico.Tipo.SELECT,
        config_json={"choices": ["presencial", "remoto"]},
        ordem=1,
    )

    primeira = auth_client.post(
        f"/api/v1/formularios/{formulario.id}/respostas",
        {
            "campo": campo.id,
            "valor_texto": "presencial",
            "owner_type": "resposta",
            "owner_id": "dummy",
        },
        format="json",
    )
    assert primeira.status_code == 201

    segunda = auth_client.post(
        f"/api/v1/formularios/{formulario.id}/respostas",
        {
            "campo": campo.id,
            "valor_texto": "remoto",
            "owner_type": "resposta",
            "owner_id": "dummy",
        },
        format="json",
    )
    assert segunda.status_code == 200
    resposta = RespostaCampoDinamico.objects.get()
    assert resposta.valor_texto == "remoto"


@pytest.mark.django_db
def test_export_job_endpoint(monkeypatch, auth_client, gt, tarefa, cliente):
    texto = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa, conteudo_html="<p>A</p>")
    called = {}

    def fake_enqueue(job_id):  # noqa: ANN001
        called["job_id"] = job_id

    monkeypatch.setattr("api.v1.viewsets.enqueue_export_job", fake_enqueue)

    resp = auth_client.post(
        "/api/v1/exports",
        {"alvo_tipo": "texto_unico", "alvo_id": str(texto.id), "formato": "pdf"},
        format="json",
    )
    assert resp.status_code == 201
    assert called["job_id"] == resp.json()["id"]


@pytest.mark.django_db
def test_quadro_endpoint_updates(auth_client, gt, cliente):
    quadro = Quadro.objects.create(cliente=cliente, gt=gt, template="default")
    resp = auth_client.put(
        f"/api/v1/quadro/{quadro.id}/celula",
        {"linha": 1, "coluna": 1, "valor_html": "Texto"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["valor_html"] == "Texto"


@pytest.mark.django_db
def test_texto_unico_endpoint_generates(monkeypatch, auth_client, gt, tarefa):
    called = {}

    def fake_enqueue(texto_unico_id):  # noqa: ANN001
        called["texto_unico_id"] = texto_unico_id

    monkeypatch.setattr("api.v1.viewsets.enqueue_texto_unico", fake_enqueue)

    resp = auth_client.post(
        "/api/v1/texto_unico/gerar",
        {"gt_id": gt.id, "tarefa_id": tarefa.id},
        format="json",
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload["gt"] == gt.id
    assert called["texto_unico_id"] == payload["id"]
