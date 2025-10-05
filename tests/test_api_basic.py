import pytest

from curriculum.models import Resposta, TextoUnico
from workshop.models import Quadro


@pytest.mark.django_db
def test_get_tarefas(auth_client, tarefa):
    resposta = auth_client.get("/api/v1/tarefas/")
    assert resposta.status_code == 200
    assert resposta.json()["results"][0]["ordem"] == 1


@pytest.mark.django_db
def test_resposta_upsert_with_etag(auth_client, gt, pergunta):
    payload = {"gt": gt.id, "pergunta": pergunta.id, "conteudo_html": "<p>Primeira resposta</p>"}
    resposta = auth_client.post("/api/v1/respostas/", payload, format="json")
    assert resposta.status_code == 201
    data = resposta.json()
    assert data["version"] == 1

    etag = resposta["ETag"]
    payload["conteudo_html"] = "<p>Atualizada</p>"
    resposta2 = auth_client.post("/api/v1/respostas/", payload, format="json", HTTP_IF_MATCH=etag)
    assert resposta2.status_code == 200
    assert resposta2.json()["version"] == 2

    conflito = auth_client.post("/api/v1/respostas/", payload, format="json", HTTP_IF_MATCH="W/\"errado\"")
    assert conflito.status_code == 412


@pytest.mark.django_db
def test_cliente_me(auth_client, usuario):
    resp = auth_client.get("/api/v1/cliente/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cliente"]["nome"] == usuario.cliente.nome


@pytest.mark.django_db
def test_texto_unico_gerar(monkeypatch, auth_client, gt, tarefa):
    chamado = {}

    def fake_enqueue(texto_unico_id):  # noqa: ANN001
        chamado["texto_unico_id"] = texto_unico_id

    monkeypatch.setattr("api.v1.viewsets.enqueue_texto_unico", fake_enqueue)

    resp = auth_client.post(
        "/api/v1/texto_unico/gerar",
        {"gt_id": gt.id, "tarefa_id": tarefa.id},
        format="json",
    )
    assert resp.status_code == 202
    assert TextoUnico.objects.filter(gt=gt, tarefa=tarefa).exists()
    assert chamado["texto_unico_id"] == TextoUnico.objects.get(gt=gt, tarefa=tarefa).id


@pytest.mark.django_db
def test_quadro_celula_update(auth_client, gt):
    quadro = Quadro.objects.create(cliente=gt.cliente, gt=gt, template="default")
    resp = auth_client.put(
        f"/api/v1/quadro/{quadro.id}/celula",
        {"linha": 1, "coluna": 1, "valor_html": "Texto"},
        format="json",
    )
    assert resp.status_code == 200
    assert quadro.celulas.count() == 1
