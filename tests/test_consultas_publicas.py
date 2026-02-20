import datetime as dt

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from consultas.models import ManifestacaoPublica


@pytest.fixture
def consulta_publica(cliente, usuario):
    from consultas.models import ConsultaPublica

    pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
    return ConsultaPublica.objects.create(
        cliente=cliente,
        titulo="Documento GT",
        slug="documento-gt",
        pdf=pdf,
        data_publicacao=dt.date.today(),
        perguntas_votacao=[{"pergunta": "Você concorda com o texto final?", "opcoes": ["Sim", "Não"]}],
        criada_por=usuario,
    )


def test_public_get_consulta(api_client, consulta_publica):
    resp = api_client.get(f"/api/v1/consultas_publicas/public/{consulta_publica.token_acesso}")
    assert resp.status_code == 200
    assert resp.data["titulo"] == consulta_publica.titulo
    assert resp.data["esta_disponivel"] is True
    assert "pdf_url" in resp.data


def test_public_post_manifestacao(api_client, consulta_publica):
    payload = {
        "nome_completo": "Maria da Silva",
        "cpf": "12345678901",
        "cidade": "Maceió",
        "estado": "AL",
        "contato_email": "maria@exemplo.com",
        "area_atuacao_profissional": "Professora",
        "comentario": "Achei o texto claro e objetivo.",
        "pagina": 3,
        "votos": ["Sim"],
    }
    resp = api_client.post(
        f"/api/v1/consultas_publicas/public/{consulta_publica.token_acesso}/manifestacoes",
        payload,
        format="json",
    )
    assert resp.status_code == 201
    assert ManifestacaoPublica.objects.filter(consulta=consulta_publica).count() == 1
    manifestacao = ManifestacaoPublica.objects.first()
    assert manifestacao.cliente_id == consulta_publica.cliente_id
    assert manifestacao.pagina == 3
    assert manifestacao.votos == ["Sim"]
    assert manifestacao.contato_email == "maria@exemplo.com"
    assert manifestacao.area_atuacao_profissional == "Professora"


def test_consulta_fechada_rejeita_manifestacao(api_client, consulta_publica):
    consulta_publica.data_fechamento = dt.date.today() - dt.timedelta(days=1)
    consulta_publica.save(update_fields=["data_fechamento"])

    resp = api_client.post(
        f"/api/v1/consultas_publicas/public/{consulta_publica.token_acesso}/manifestacoes",
        {
            "nome_completo": "João",
            "cpf": "12345678901",
            "cidade": "Arapiraca",
            "estado": "AL",
            "contato_email": "joao@exemplo.com",
            "area_atuacao_profissional": "Gestor escolar",
            "comentario": "Comentário tardio",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert ManifestacaoPublica.objects.filter(consulta=consulta_publica).count() == 0
