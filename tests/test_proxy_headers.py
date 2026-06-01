import pytest
from django.test import RequestFactory


@pytest.fixture(autouse=True)
def habilitar_flags():
    pass


def test_absolute_urls_use_forwarded_https_scheme(settings):
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    settings.ALLOWED_HOSTS = ["referencial-vi5w.onrender.com"]

    request = RequestFactory().get(
        "/api/v1/consultas_publicas/public/token",
        HTTP_HOST="referencial-vi5w.onrender.com",
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert request.build_absolute_uri("/media/consultas/doc.pdf").startswith(
        "https://referencial-vi5w.onrender.com/"
    )
