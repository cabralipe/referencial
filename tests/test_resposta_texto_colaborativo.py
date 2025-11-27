import pytest
from rest_framework.reverse import reverse

from core.models import Usuario
from curriculum.models import Resposta, TextoColaborativo


@pytest.mark.django_db
def test_resposta_sincroniza_texto_colaborativo(api_client, cliente, gt, pergunta, membro_gt, monkeypatch):
    gt.membros.add(membro_gt)
    api_client.force_authenticate(membro_gt)

    captured = []

    def fake_broadcast(alvo_tipo, alvo_id, event, payload):  # noqa: ANN001
        captured.append((alvo_tipo, alvo_id, event, payload))

    monkeypatch.setattr("curriculum.services.collab_sync.broadcast_stream_event", fake_broadcast)

    url = reverse('resposta-list')
    response = api_client.post(
        url,
        {
            "gt": gt.id,
            "pergunta": pergunta.id,
            "conteudo_html": "<p>Resposta inicial</p>",
        },
        format='json',
    )

    assert response.status_code == 201
    data = response.json()
    texto = TextoColaborativo.objects.get(gt=gt, pergunta=pergunta)
    assert texto.cliente_id == cliente.id
    assert texto.autor_id == membro_gt.id
    assert "collab-resposta-texto" in texto.conteudo_html
    assert str(pergunta.id) in texto.conteudo_html

    events = {(alvo_tipo, event) for (alvo_tipo, _, event, _) in captured}
    assert ("texto_colaborativo_list", "collab_text:created") in events
    assert ("texto_colaborativo", "collab_text:updated") in events

    resposta_id = data["id"]
    url_detail = reverse('resposta-detail', kwargs={"pk": resposta_id})
    response_update = api_client.put(
        url_detail,
        {
            "gt": gt.id,
            "pergunta": pergunta.id,
            "conteudo_html": "<p>Resposta atualizada</p>",
        },
        format='json',
        HTTP_IF_MATCH=data["etag"],
    )
    assert response_update.status_code == 200
    texto.refresh_from_db()
    assert texto.version == 2
    assert "Resposta atualizada" in texto.conteudo_html


@pytest.mark.django_db
def test_super_admin_sem_cliente_usa_cliente_do_gt(api_client, gt, pergunta, django_user_model):
    super_admin: Usuario = django_user_model.objects.create_user(
        email="root@test.com",
        password="senha123",
        nome="Root",
        role=Usuario.Role.SUPER_ADMIN,
        cliente=None,
    )
    api_client.force_authenticate(super_admin)

    response = api_client.post(
        reverse('resposta-list'),
        {
            "gt": gt.id,
            "pergunta": pergunta.id,
            "conteudo_html": "<p>Conteúdo super admin</p>",
        },
        format='json',
    )

    assert response.status_code == 201
    data = response.json()
    resposta = Resposta.objects.get(pk=data["id"])
    texto = TextoColaborativo.objects.get(pergunta=pergunta, gt=gt)
    assert resposta.cliente_id == gt.cliente_id
    assert texto.cliente_id == gt.cliente_id
