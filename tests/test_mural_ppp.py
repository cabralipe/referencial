import pytest

from core.models import Cliente
from curriculum.models import Tarefa


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
def test_ppp_config_filtra_tarefas_do_cliente(api_client, usuario, cliente):
    outro_cliente = Cliente.objects.create(nome="Outro", slug="outro")
    tarefa_valida = Tarefa.objects.create(cliente=cliente, ordem=1, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)
    tarefa_invalida = Tarefa.objects.create(cliente=outro_cliente, ordem=2, etapa="II", tipo=Tarefa.Tipo.PERGUNTAS)

    api_client.force_authenticate(usuario)
    resp = api_client.patch(
        "/api/v1/ppp/config",
        {"tarefa_ids": [tarefa_valida.id, tarefa_invalida.id]},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["tarefa_ids"] == [tarefa_valida.id]

    resp = api_client.get("/api/v1/ppp")
    assert resp.status_code == 200
    trilhas = resp.json().get("trilhas", [])
    assert len(trilhas) == 1
    assert trilhas[0]["id"] == tarefa_valida.id
