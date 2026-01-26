import pytest


@pytest.mark.django_db
def test_redator_can_create_mural(api_client, articulador):
    api_client.force_authenticate(articulador)
    response = api_client.post(
        "/api/v1/mural",
        {"titulo": "Aviso", "conteudo_html": "<p>Conteúdo</p>"},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["titulo"] == "Aviso"


@pytest.mark.django_db
def test_membro_gt_cannot_create_mural(api_client, membro_gt):
    api_client.force_authenticate(membro_gt)
    response = api_client.post(
        "/api/v1/mural",
        {"titulo": "Aviso", "conteudo_html": "<p>Conteúdo</p>"},
        format="json",
    )
    assert response.status_code == 403
