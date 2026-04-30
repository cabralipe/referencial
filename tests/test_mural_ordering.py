import pytest

from notifications.models import Notificacao


@pytest.mark.django_db
def test_mural_update_preserves_position_when_not_sent(api_client, articulador):
    api_client.force_authenticate(articulador)

    first = api_client.post(
        "/api/v1/mural",
        {"titulo": "Primeiro", "conteudo_html": "<p>Primeiro</p>", "position": 0},
        format="json",
    )
    second = api_client.post(
        "/api/v1/mural",
        {"titulo": "Segundo", "conteudo_html": "<p>Segundo</p>", "position": 1},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    second_id = second.json()["id"]
    update = api_client.put(
        f"/api/v1/mural/{second_id}",
        {"titulo": "Segundo editado", "conteudo_html": "<p>Atualizado</p>"},
        format="json",
    )

    assert update.status_code == 200
    assert update.json()["position"] == 1

    listed = api_client.get("/api/v1/mural")

    assert listed.status_code == 200
    payload = listed.json()
    assert [item["id"] for item in payload] == [first.json()["id"], second_id]
    assert [item["position"] for item in payload] == [0, 1]


@pytest.mark.django_db
def test_mural_order_does_not_change_after_edit_when_positions_match(api_client, articulador):
    api_client.force_authenticate(articulador)

    first = api_client.post(
        "/api/v1/mural",
        {"titulo": "Primeiro", "conteudo_html": "<p>Primeiro</p>", "position": 0},
        format="json",
    )
    second = api_client.post(
        "/api/v1/mural",
        {"titulo": "Segundo", "conteudo_html": "<p>Segundo</p>", "position": 0},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    initial_ids = [item["id"] for item in api_client.get("/api/v1/mural").json()]

    updated = api_client.put(
        f"/api/v1/mural/{first.json()['id']}",
        {"titulo": "Primeiro revisado", "conteudo_html": "<p>Revisado</p>"},
        format="json",
    )

    assert updated.status_code == 200

    final_ids = [item["id"] for item in api_client.get("/api/v1/mural").json()]

    assert final_ids == initial_ids


@pytest.mark.django_db
def test_mural_reorder_updates_position_without_touching_updated_at(api_client, articulador):
    api_client.force_authenticate(articulador)

    first = api_client.post(
        "/api/v1/mural",
        {"titulo": "Primeiro", "conteudo_html": "<p>Primeiro</p>", "position": 0},
        format="json",
    )
    second = api_client.post(
        "/api/v1/mural",
        {"titulo": "Segundo", "conteudo_html": "<p>Segundo</p>", "position": 1},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    before = {
        notificacao.payload_json["mural_id"]: notificacao.updated_at
        for notificacao in Notificacao.objects.filter(tipo="mural_post").order_by("id")
    }

    response = api_client.post(
        "/api/v1/mural/reorder",
        [
            {"id": first.json()["id"], "position": 1},
            {"id": second.json()["id"], "position": 0},
        ],
        format="json",
    )

    assert response.status_code == 200

    after = {
        notificacao.payload_json["mural_id"]: notificacao.updated_at
        for notificacao in Notificacao.objects.filter(tipo="mural_post").order_by("id")
    }

    assert after == before

    listed = api_client.get("/api/v1/mural")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [second.json()["id"], first.json()["id"]]
