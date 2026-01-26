import pytest

from curriculum.models import GT, Pergunta, Resposta, Tarefa
from reviews.models import Revisao


@pytest.mark.django_db
def test_progresso_trilha_atualiza_status(auth_client, cliente, membro_gt):
    tarefa = Tarefa.objects.create(cliente=cliente, ordem=1, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)
    pergunta = Pergunta.objects.create(cliente=cliente, tarefa=tarefa, ordem=1, texto="Missão")
    gt = GT.objects.create(cliente=cliente, nome="GT 1", etapa="I")
    gt.membros.add(membro_gt)

    auth_client.force_authenticate(membro_gt)
    resp = auth_client.get(f"/api/v1/tarefas/{tarefa.id}/progresso", {"gt_id": gt.id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "nao_iniciado"

    resposta = Resposta.objects.create(cliente=cliente, gt=gt, pergunta=pergunta, conteudo_html="<p>Texto</p>")
    resp = auth_client.get(f"/api/v1/tarefas/{tarefa.id}/progresso", {"gt_id": gt.id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "em_andamento"

    Revisao.objects.create(
        cliente=cliente,
        alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
        alvo_id=str(resposta.id),
        status=Revisao.Status.EM_REVISAO,
        solicitante=membro_gt,
    )
    resp = auth_client.get(f"/api/v1/tarefas/{tarefa.id}/progresso", {"gt_id": gt.id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "em_revisao"

    Revisao.objects.create(
        cliente=cliente,
        alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
        alvo_id=str(resposta.id),
        status=Revisao.Status.APROVADO,
        solicitante=membro_gt,
    )
    resp = auth_client.get(f"/api/v1/tarefas/{tarefa.id}/progresso", {"gt_id": gt.id})
    assert resp.status_code == 200
    assert resp.json()["status"] == "concluido"
