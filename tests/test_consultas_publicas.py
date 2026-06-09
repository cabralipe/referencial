import datetime as dt
import json
import zipfile
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from consultas.models import FormularioInscricao, InscricaoPublica, ManifestacaoPublica


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


def test_inscricao_publica_aceita_campo_upload_de_arquivo(api_client, cliente, usuario, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    formulario = FormularioInscricao.objects.create(
        cliente=cliente,
        titulo="Inscricao com arquivo",
        ativo=True,
        campos_config=[
            {"chave": "nome_completo", "label": "Nome completo", "tipo": "text", "obrigatorio": True, "ordem": 1, "ativo": True, "padrao": True},
            {"chave": "comprovante", "label": "Comprovante", "tipo": "file", "obrigatorio": True, "ordem": 2, "ativo": True, "padrao": False},
        ],
        criado_por=usuario,
    )
    arquivo = SimpleUploadedFile("comprovante.pdf", b"%PDF-1.4 arquivo", content_type="application/pdf")

    resp = api_client.post(
        f"/api/v1/formularios_inscricao/public/{formulario.token_acesso}/inscricoes",
        {
            "nome_completo": "Maria da Silva",
            "areas_atuacao": json.dumps(["Educacao"]),
            "representacoes": json.dumps(["Professor"]),
            "dados_extras": json.dumps({"observacao": "enviado"}),
            "comprovante": arquivo,
        },
        format="multipart",
    )

    assert resp.status_code == 201
    inscricao = InscricaoPublica.objects.get(formulario=formulario)
    comprovante = inscricao.dados_extras["comprovante"]
    assert comprovante["nome"] == "comprovante.pdf"
    assert comprovante["content_type"] == "application/pdf"
    assert comprovante["path"].startswith(f"inscricoes/cliente_{cliente.id}/formulario_{formulario.id}/comprovante/")
    assert inscricao.dados_extras["observacao"] == "enviado"


def test_admin_lista_e_baixa_anexos_de_inscricoes(auth_client, api_client, cliente, usuario, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    formulario = FormularioInscricao.objects.create(
        cliente=cliente,
        titulo="Inscricao com anexos",
        ativo=True,
        campos_config=[
            {"chave": "nome_completo", "label": "Nome completo", "tipo": "text", "obrigatorio": True, "ordem": 1, "ativo": True, "padrao": True},
            {"chave": "comprovante", "label": "Comprovante de representacao", "tipo": "file", "obrigatorio": True, "ordem": 2, "ativo": True, "padrao": False},
        ],
        criado_por=usuario,
    )
    arquivo = SimpleUploadedFile("comprovante.pdf", b"%PDF-1.4 arquivo", content_type="application/pdf")
    create_resp = api_client.post(
        f"/api/v1/formularios_inscricao/public/{formulario.token_acesso}/inscricoes",
        {"nome_completo": "Maria da Silva", "comprovante": arquivo},
        format="multipart",
    )
    assert create_resp.status_code == 201

    list_resp = auth_client.get(f"/api/v1/formularios_inscricao/{formulario.id}/anexos")

    assert list_resp.status_code == 200
    assert len(list_resp.data) == 1
    anexo = list_resp.data[0]
    assert anexo["participante"] == "Maria da Silva"
    assert anexo["campo_label"] == "Comprovante de representacao"
    assert anexo["nome"] == "comprovante.pdf"

    zip_resp = auth_client.post(
        f"/api/v1/formularios_inscricao/{formulario.id}/anexos/download",
        {"ids": [anexo["id"]]},
        format="json",
    )

    assert zip_resp.status_code == 200
    assert zip_resp["Content-Type"] == "application/zip"
    with zipfile.ZipFile(BytesIO(zip_resp.content)) as zip_file:
        nomes = zip_file.namelist()
        assert len(nomes) == 1
        assert nomes[0].endswith("comprovante.pdf")
        assert zip_file.read(nomes[0]) == b"%PDF-1.4 arquivo"
