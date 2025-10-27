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
