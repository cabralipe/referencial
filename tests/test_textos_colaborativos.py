import pytest
from rest_framework.reverse import reverse

from curriculum.models import TextoColaborativo
from core.models import Usuario


@pytest.mark.django_db
def test_membro_gt_cria_texto_colaborativo(api_client, cliente, gt, membro_gt, monkeypatch):
    gt.membros.add(membro_gt)
    api_client.force_authenticate(membro_gt)

    captured = []

    def fake_broadcast(alvo_tipo, alvo_id, event, payload):  # noqa: ANN001
        captured.append((alvo_tipo, alvo_id, event, payload))

    monkeypatch.setattr("api.v1.viewsets.broadcast_stream_event", fake_broadcast)

    url = reverse('texto_colaborativo-list')
    payload = {
        'gt': gt.id,
        'titulo': 'Manifesto do GT',
        'conteudo_html': '<p>Conteúdo inicial</p>',
    }
    response = api_client.post(url, payload, format='json')

    assert response.status_code == 201
    data = response.json()
    assert data['gt'] == gt.id
    assert data['pergunta'] is None
    assert data['titulo'] == 'Manifesto do GT'
    assert data['conteudo_html'] == '<p>Conteúdo inicial</p>'
    assert data['autor'] == membro_gt.id
    assert data['version'] == 1
    assert data['etag']

    texto = TextoColaborativo.objects.get(pk=data['id'])
    assert texto.cliente_id == cliente.id
    assert texto.autor_id == membro_gt.id

    # Garante broadcast para lista e documento individual
    events = {(alvo_tipo, event) for (alvo_tipo, _, event, _) in captured}
    assert ("texto_colaborativo_list", "collab_text:created") in events
    assert ("texto_colaborativo", "collab_text:updated") in events


@pytest.mark.django_db
def test_edicao_incrementa_versao_e_broadcast(api_client, cliente, gt, membro_gt, django_user_model, monkeypatch):
    outro = django_user_model.objects.create_user(
        email='outro@teste.com',
        password='senha123',
        nome='Outro Membro',
        cliente=cliente,
        role=Usuario.Role.MEMBRO_GT,
    )
    gt.membros.add(membro_gt, outro)

    texto = TextoColaborativo.objects.create(
        cliente=cliente,
        gt=gt,
        titulo='Rascunho',
        conteudo_html='Versão 1',
        autor=membro_gt,
    )

    api_client.force_authenticate(outro)

    captured = []

    def fake_broadcast(alvo_tipo, alvo_id, event, payload):  # noqa: ANN001
        captured.append((alvo_tipo, alvo_id, event, payload))

    monkeypatch.setattr("api.v1.viewsets.broadcast_stream_event", fake_broadcast)

    url = reverse('texto_colaborativo-detail', kwargs={'pk': texto.id})
    response = api_client.put(
        url,
        {
            'titulo': 'Rascunho atualizado',
            'conteudo_html': 'Nova versão',
        },
        format='json',
        HTTP_IF_MATCH=texto.etag,
    )

    assert response.status_code == 200
    data = response.json()
    assert data['version'] == 2
    assert data['titulo'] == 'Rascunho atualizado'
    assert data['conteudo_html'] == 'Nova versão'
    assert data['autor'] == outro.id
    assert data['pergunta'] is None
    assert response['ETag'] == data['etag']

    texto.refresh_from_db()
    assert texto.version == 2
    assert texto.autor_id == outro.id

    events = {(alvo_tipo, event) for (alvo_tipo, _, event, _) in captured}
    assert ("texto_colaborativo_list", "collab_text:updated") in events
    assert ("texto_colaborativo", "collab_text:updated") in events


@pytest.mark.django_db
def test_usuario_sem_vinculo_nao_cria_texto(api_client, cliente, gt, django_user_model):
    outsider = django_user_model.objects.create_user(
        email='externo@teste.com',
        password='senha123',
        nome='Externo',
        cliente=cliente,
        role=Usuario.Role.MEMBRO_GT,
    )
    api_client.force_authenticate(outsider)

    url = reverse('texto_colaborativo-list')
    response = api_client.post(
        url,
        {
            'gt': gt.id,
            'titulo': 'Não autorizado',
            'conteudo_html': 'Sem acesso',
        },
        format='json',
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_atualizacao_em_lote(api_client, cliente, gt, membro_gt, monkeypatch):
    gt.membros.add(membro_gt)
    api_client.force_authenticate(membro_gt)

    texto1 = TextoColaborativo.objects.create(
        cliente=cliente,
        gt=gt,
        titulo='Primeiro',
        conteudo_html='A',
        autor=membro_gt,
    )
    texto2 = TextoColaborativo.objects.create(
        cliente=cliente,
        gt=gt,
        titulo='Segundo',
        conteudo_html='B',
        autor=membro_gt,
    )

    captured = []

    def fake_broadcast(alvo_tipo, alvo_id, event, payload):  # noqa: ANN001
        captured.append((alvo_tipo, alvo_id, event, payload))

    monkeypatch.setattr("curriculum.services.collab_sync.broadcast_stream_event", fake_broadcast)

    url = reverse('texto_colaborativo-lote')
    response = api_client.put(
        url,
        {
            "textos": [
                {"id": texto1.id, "titulo": "Primeiro v2", "conteudo_html": "A2", "etag": texto1.etag},
                {"id": texto2.id, "titulo": "Segundo v2", "conteudo_html": "B2", "etag": texto2.etag},
            ]
        },
        format='json',
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["updated"]) == 2
    assert body["errors"] == []

    texto1.refresh_from_db()
    texto2.refresh_from_db()
    assert texto1.version == 2
    assert texto2.version == 2

    events = {(alvo_tipo, event) for (alvo_tipo, _, event, _) in captured}
    assert ("texto_colaborativo_list", "collab_text:updated") in events
    assert ("texto_colaborativo", "collab_text:updated") in events

    # Segundo round com ETag desatualizado
    response = api_client.put(
        url,
        {
            "textos": [
                {"id": texto1.id, "titulo": "Primeiro v3", "conteudo_html": "A3", "etag": "stale"},
            ]
        },
        format='json',
    )
    assert response.status_code == 207
    body = response.json()
    assert body["updated"] == []
    assert body["errors"][0]["id"] == texto1.id
