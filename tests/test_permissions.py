import pytest

from core.models import Cliente, Usuario
from curriculum.models import GT, Pergunta, Resposta, Tarefa


@pytest.mark.django_db
def test_respostas_filtra_por_cliente(auth_client, usuario):
    outro_cliente = Cliente.objects.create(nome="Outro", slug="outro")
    gt_outro = GT.objects.create(cliente=outro_cliente, nome="GT 2", etapa="II")
    tarefa = Tarefa.objects.create(cliente=outro_cliente, ordem=1, etapa="II", tipo=Tarefa.Tipo.PERGUNTAS)
    tarefa.gts.add(gt_outro)
    pergunta = Pergunta.objects.create(cliente=outro_cliente, tarefa=tarefa, ordem=1, texto="Pergunta")
    Resposta.objects.create(cliente=outro_cliente, gt=gt_outro, pergunta=pergunta, conteudo_html="<p>alheio</p>")

    resp = auth_client.get("/api/v1/respostas/")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.django_db
def test_super_admin_pode_alterar_cliente(api_client, cliente):
    super_admin = Usuario.objects.create_superuser(
        email="super@admin.com",
        password="senha123",
        nome="Super",
    )
    api_client.force_authenticate(super_admin)
    resp = api_client.get("/api/v1/cliente/me", HTTP_X_CLIENTE_ID=str(cliente.id))
    assert resp.status_code == 200
    assert resp.json()["cliente"]["id"] == cliente.id


@pytest.mark.django_db
def test_requer_autenticacao(api_client):
    resp = api_client.get("/api/v1/tarefas")
    assert resp.status_code in {401, 403}
