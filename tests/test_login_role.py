import pytest

from core.models import Usuario


def _error_messages(payload: dict) -> str:
    if isinstance(payload, dict):
        for key in ("non_field_errors", "detail"):
            value = payload.get(key)
            if isinstance(value, list):
                return " ".join(str(item) for item in value)
            if isinstance(value, str):
                return value
    return str(payload)


@pytest.mark.django_db
def test_login_rejects_invalid_role(api_client, membro_gt):
    response = api_client.post(
        "/api/v1/auth/login",
        {"email": membro_gt.email, "password": "senha123", "role": "revisor"},
        format="json",
    )
    assert response.status_code == 400
    message = _error_messages(response.json())
    assert "perfil selecionado" in message.lower()


@pytest.mark.django_db
def test_login_allows_matching_role(api_client, membro_gt):
    response = api_client.post(
        "/api/v1/auth/login",
        {"email": membro_gt.email, "password": "senha123", "role": "membro_gt"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == membro_gt.email
    assert body["user"]["role"] == Usuario.Role.MEMBRO_GT
