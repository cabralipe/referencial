import pytest

from curriculum.models import GT, Pergunta, Resposta, Tarefa


@pytest.mark.django_db
def test_membro_gt_ve_apenas_tarefas_relacionadas(api_client, cliente, membro_gt):
    gt_proprio = GT.objects.create(cliente=cliente, nome="GT Educação Especial", etapa="I")
    gt_outro = GT.objects.create(cliente=cliente, nome="GT EJA", etapa="II")
    gt_proprio.membros.add(membro_gt)

    tarefa_propria = Tarefa.objects.create(
        cliente=cliente,
        nome="Tarefa do meu GT",
        ordem=1,
        etapa="I",
        tipo=Tarefa.Tipo.PERGUNTAS,
    )
    pergunta_propria = Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa_propria,
        ordem=1,
        texto="Pergunta do meu GT",
    )
    pergunta_propria.gts.add(gt_proprio)

    tarefa_sem_gt = Tarefa.objects.create(
        cliente=cliente,
        nome="Tarefa aberta",
        ordem=2,
        etapa="I",
        tipo=Tarefa.Tipo.PERGUNTAS,
    )
    Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa_sem_gt,
        ordem=1,
        texto="Pergunta sem GT específico",
    )

    tarefa_outro_gt = Tarefa.objects.create(
        cliente=cliente,
        nome="Tarefa de outro GT",
        ordem=3,
        etapa="II",
        tipo=Tarefa.Tipo.PERGUNTAS,
    )
    pergunta_outro = Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa_outro_gt,
        ordem=1,
        texto="Pergunta de outro GT",
    )
    pergunta_outro.gts.add(gt_outro)

    api_client.force_authenticate(membro_gt)
    resposta = api_client.get("/api/v1/tarefas")
    assert resposta.status_code == 200
    nomes = {item["nome"] for item in resposta.json().get("results", [])}
    assert tarefa_propria.nome in nomes
    assert tarefa_sem_gt.nome in nomes
    assert tarefa_outro_gt.nome not in nomes


@pytest.mark.django_db
def test_membro_gt_ve_apenas_respostas_do_seu_gt(api_client, cliente, membro_gt):
    gt_proprio = GT.objects.create(cliente=cliente, nome="GT Educação Especial", etapa="I")
    gt_outro = GT.objects.create(cliente=cliente, nome="GT EJA", etapa="II")
    gt_proprio.membros.add(membro_gt)

    tarefa = Tarefa.objects.create(
        cliente=cliente,
        nome="Tarefa",
        ordem=1,
        etapa="I",
        tipo=Tarefa.Tipo.PERGUNTAS,
    )
    pergunta_propria = Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa,
        ordem=1,
        texto="Pergunta do meu GT",
    )
    pergunta_propria.gts.add(gt_proprio)
    pergunta_outro = Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa,
        ordem=2,
        texto="Pergunta de outro GT",
    )
    pergunta_outro.gts.add(gt_outro)

    Resposta.objects.create(
        cliente=cliente,
        gt=gt_proprio,
        pergunta=pergunta_propria,
        conteudo_html="<p>Meu GT</p>",
    )
    Resposta.objects.create(
        cliente=cliente,
        gt=gt_outro,
        pergunta=pergunta_outro,
        conteudo_html="<p>Outro GT</p>",
    )

    api_client.force_authenticate(membro_gt)
    resposta = api_client.get("/api/v1/respostas")
    assert resposta.status_code == 200
    resultados = resposta.json().get("results", [])
    assert {item["gt"] for item in resultados} == {gt_proprio.id}
