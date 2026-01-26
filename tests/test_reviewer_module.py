import pytest

from comments.models import Comentario
from curriculum.models import Resposta, Tarefa
from reviews.models import ReviewDecision, ReviewerAssignment, Revisao


@pytest.fixture
def revisor(cliente, django_user_model):
    return django_user_model.objects.create_user(
        email="revisor@teste.com",
        password="senha123",
        nome="Revisor",
        cliente=cliente,
        role=django_user_model.Role.REVISOR,
    )


def _criar_revisao_resposta(*, cliente, gt, pergunta, solicitante):
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Texto</p>",
        autor=solicitante,
    )
    revisao = Revisao.objects.create(
        cliente=cliente,
        alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
        alvo_id=str(resposta.id),
        status=Revisao.Status.EM_REVISAO,
        solicitante=solicitante,
    )
    return resposta, revisao


def test_revisor_scope_assignment(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )

    api_client.force_authenticate(revisor)
    response = api_client.get("/api/v1/revisoes")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert revisao.id in ids


def test_revisor_sem_assignment_nao_ve_revisoes(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)

    api_client.force_authenticate(revisor)
    response = api_client.get("/api/v1/revisoes")
    assert response.status_code == 200
    assert response.json() == []


def test_revisor_respeita_municipio(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )

    from core.models import Cliente, Usuario
    from curriculum.models import GT, Pergunta

    cliente_b = Cliente.objects.create(nome="Prefeitura B", slug="prefeitura-b")
    gt_b = GT.objects.create(cliente=cliente_b, nome="GT B", etapa="I")
    tarefa_b = Tarefa.objects.create(cliente=cliente_b, ordem=2, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)
    pergunta_b = Pergunta.objects.create(cliente=cliente_b, tarefa=tarefa_b, ordem=1, texto="Pergunta B")
    membro_b = Usuario.objects.create_user(
        email="membrob@teste.com",
        password="senha123",
        nome="Membro B",
        cliente=cliente_b,
        role=Usuario.Role.MEMBRO_GT,
    )
    _resposta_b, revisao_b = _criar_revisao_resposta(cliente=cliente_b, gt=gt_b, pergunta=pergunta_b, solicitante=membro_b)

    api_client.force_authenticate(revisor)
    response = api_client.get("/api/v1/revisoes")
    ids = [item["id"] for item in response.json()]
    assert revisao.id in ids
    assert revisao_b.id not in ids


def test_revisor_recommendation(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )

    api_client.force_authenticate(revisor)
    response = api_client.post(
        f"/api/v1/revisoes/{revisao.id}/recommend",
        data={"decision": "approve", "note": "Ok", "checklist": ["Clareza"]},
        format="json",
    )
    assert response.status_code == 200
    assert ReviewDecision.objects.filter(
        cliente=cliente,
        target_type=revisao.alvo_tipo,
        target_id=revisao.alvo_id,
        actor=revisor,
    ).exists()


def test_revisor_nao_pode_decidir_status(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )

    api_client.force_authenticate(revisor)
    response = api_client.post(
        f"/api/v1/revisoes/{revisao.id}/decisao",
        data={"decision": "approve"},
        format="json",
    )
    assert response.status_code == 403


def test_revisor_nao_acessa_admin_console(api_client, revisor):
    api_client.force_authenticate(revisor)
    response = api_client.get("/api/v1/admin/usuarios")
    assert response.status_code == 403


def test_revisor_comentario_criar_resolver(api_client, cliente, tarefa, pergunta, gt, membro_gt, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )

    api_client.force_authenticate(revisor)
    response = api_client.post(
        "/api/v1/comentarios",
        data={
            "alvo_tipo": "resposta",
            "alvo_id": revisao.alvo_id,
            "conteudo_html": "<p>Comentário</p>",
            "anchor_json": {"context": "linha"},
        },
        format="json",
    )
    assert response.status_code == 201
    comentario_id = response.json()["id"]
    comentario = Comentario.objects.get(pk=comentario_id)
    assert comentario.autor_id == revisor.id

    etag = response.headers.get("ETag")
    response_update = api_client.put(
        f"/api/v1/comentarios/{comentario_id}",
        data={"resolvido": True},
        format="json",
        HTTP_IF_MATCH=etag,
    )
    assert response_update.status_code == 200
    comentario.refresh_from_db()
    assert comentario.resolvido is True


def test_redator_visualiza_recomendacao(api_client, cliente, tarefa, pergunta, gt, membro_gt, articulador, revisor):
    _resposta, revisao = _criar_revisao_resposta(cliente=cliente, gt=gt, pergunta=pergunta, solicitante=membro_gt)
    gt.membros.add(articulador)
    ReviewerAssignment.objects.create(
        cliente=cliente,
        reviewer=revisor,
        scope_type=ReviewerAssignment.ScopeType.TRAIL,
        scope_id=str(tarefa.id),
    )
    ReviewDecision.objects.create(
        cliente=cliente,
        target_type=revisao.alvo_tipo,
        target_id=revisao.alvo_id,
        actor=revisor,
        actor_role=ReviewDecision.ActorRole.REVIEWER,
        decision_type=ReviewDecision.DecisionType.RECOMMEND_MINOR,
        checklist=["Clareza"],
        note="Ajustes leves",
    )

    api_client.force_authenticate(articulador)
    response = api_client.get(f"/api/v1/revisoes/{revisao.id}")
    assert response.status_code == 200
    assert response.json().get("reviewer_recommendation") is not None


def test_revisor_inbox_view_permission(client, revisor, usuario):
    client.force_login(revisor)
    response = client.get("/revisor/inbox")
    assert response.status_code == 200

    client.force_login(usuario)
    response = client.get("/revisor/inbox")
    assert response.status_code == 403
