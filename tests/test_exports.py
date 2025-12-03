from io import BytesIO

import pytest

from curriculum.models import GT, Pergunta, Resposta, Tarefa, TextoUnico
from api.v1.serializers import ExportJobSerializer
from core.models import Cliente
from exports.models import ExportJob
from exports.services.docx import Document as DocxDocument, html_to_docx_bytes
from tasks.exports import build_docx, build_pdf


class DummyProvider:
    def render_pdf(self, ctx):
        return b"pdf"

    def render_docx(self, ctx):
        return b"docx"


@pytest.mark.django_db
def test_build_pdf(settings, monkeypatch, cliente, gt, tarefa):
    settings.MEDIA_ROOT = settings.BASE_DIR / "media"
    texto = TextoUnico.objects.create(
        cliente=cliente,
        gt=gt,
        tarefa=tarefa,
        conteudo_html="<p>Teste</p>",
    )
    job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.TEXTO_UNICO,
        alvo_id=str(texto.id),
        formato=ExportJob.Formato.PDF,
    )

    monkeypatch.setattr("tasks.exports.get_export_provider", lambda *_args, **_kwargs: DummyProvider())

    build_pdf(job.id)
    job.refresh_from_db()
    assert job.status == ExportJob.Status.DONE
    assert job.url_resultado


@pytest.mark.django_db
def test_build_docx(settings, monkeypatch, cliente, gt, tarefa):
    settings.MEDIA_ROOT = settings.BASE_DIR / "media"
    texto = TextoUnico.objects.create(
        cliente=cliente,
        gt=gt,
        tarefa=tarefa,
        conteudo_html="<p>Teste</p>",
    )
    job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.TEXTO_UNICO,
        alvo_id=str(texto.id),
        formato=ExportJob.Formato.DOCX,
    )

    monkeypatch.setattr("tasks.exports.get_export_provider", lambda *_args, **_kwargs: DummyProvider())

    build_docx(job.id)
    job.refresh_from_db()
    assert job.status == ExportJob.Status.DONE
    assert job.url_resultado


@pytest.mark.django_db
def test_export_job_serializer_blocks_cross_cliente(cliente, usuario, gt, tarefa):
    other_cliente = Cliente.objects.create(nome="Prefeitura Extra", slug="prefeitura-extra")
    other_gt = GT.objects.create(cliente=other_cliente, nome="GT Extra", etapa="I")
    other_tarefa = Tarefa.objects.create(cliente=other_cliente, ordem=1, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)
    texto_estrangeiro = TextoUnico.objects.create(cliente=other_cliente, gt=other_gt, tarefa=other_tarefa)

    request = type("Req", (), {"user": usuario})()
    serializer = ExportJobSerializer(
        data={
            "alvo_tipo": ExportJob.AlvoTipo.TEXTO_UNICO,
            "alvo_id": str(texto_estrangeiro.id),
            "formato": ExportJob.Formato.PDF,
        },
        context={"request": request},
    )

    assert serializer.is_valid() is False
    assert "alvo_id" in serializer.errors

    texto_local = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa)
    serializer_ok = ExportJobSerializer(
        data={
            "alvo_tipo": ExportJob.AlvoTipo.TEXTO_UNICO,
            "alvo_id": str(texto_local.id),
            "formato": ExportJob.Formato.PDF,
        },
        context={"request": request},
    )

    assert serializer_ok.is_valid(), serializer_ok.errors


@pytest.mark.django_db
def test_export_job_serializer_accepts_colecao(cliente, usuario, gt, tarefa):
    pergunta = Pergunta.objects.create(cliente=cliente, tarefa=tarefa, ordem=1, texto="Pergunta 1")
    resposta = Resposta.objects.create(cliente=cliente, gt=gt, pergunta=pergunta, conteudo_html="<p>Oi</p>")

    request = type("Req", (), {"user": usuario})()
    serializer = ExportJobSerializer(
        data={
            "alvo_tipo": ExportJob.AlvoTipo.COLECAO,
            "alvo_id": "",
            "formato": ExportJob.Formato.PDF,
            "payload_json": {"secoes": [{"tipo": ExportJob.AlvoTipo.RESPOSTA, "id": resposta.id, "titulo": "Primeira"}]},
        },
        context={"request": request},
    )

    assert serializer.is_valid(), serializer.errors
    instance = serializer.save(cliente_id=cliente.id)
    assert instance.payload_json["secoes"][0]["id"] == resposta.id


@pytest.mark.skipif(DocxDocument is None, reason="python-docx não está disponível")
def test_html_to_docx_preserva_paragrafos():
    context = {
        "titulo": "Relatório",
        "conteudo_html": "<p>Primeiro parágrafo</p><p>Segundo parágrafo</p><ul><li>Item 1</li><li>Item 2</li></ul>",
    }

    data = html_to_docx_bytes(context)
    doc = DocxDocument(BytesIO(data))

    textos = [p.text for p in doc.paragraphs]
    assert textos[0] == "Relatório"
    assert textos[1:5] == ["Primeiro parágrafo", "Segundo parágrafo", "Item 1", "Item 2"]


@pytest.mark.django_db
def test_build_context_quadro_respeita_colunas(cliente, gt):
    from tasks.exports import _build_context
    from workshop.models import CelulaQuadro, Quadro

    quadro = Quadro.objects.create(cliente=cliente, gt=gt, template="Modelo")
    CelulaQuadro.objects.create(cliente=cliente, quadro=quadro, linha=1, coluna=1, valor_html="A1")
    CelulaQuadro.objects.create(cliente=cliente, quadro=quadro, linha=1, coluna=2, valor_html="A2")
    CelulaQuadro.objects.create(cliente=cliente, quadro=quadro, linha=2, coluna=1, valor_html="B1")

    job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.QUADRO,
        alvo_id=str(quadro.id),
        formato=ExportJob.Formato.PDF,
    )

    contexto = _build_context(job)
    conteudo = contexto.payload["conteudo_html"]

    assert "<tr><td>A1</td><td>A2</td></tr>" in conteudo
    assert "<tr><td>B1</td></tr>" in conteudo


@pytest.mark.django_db
def test_build_context_colecao_respeita_ordem(cliente, gt):
    from tasks.exports import _build_context

    tarefa = Tarefa.objects.create(cliente=cliente, ordem=1, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)
    pergunta1 = Pergunta.objects.create(cliente=cliente, tarefa=tarefa, ordem=1, texto="Primeira")
    pergunta2 = Pergunta.objects.create(cliente=cliente, tarefa=tarefa, ordem=2, texto="Segunda")
    resposta1 = Resposta.objects.create(cliente=cliente, gt=gt, pergunta=pergunta1, conteudo_html="<p>A</p>")
    resposta2 = Resposta.objects.create(cliente=cliente, gt=gt, pergunta=pergunta2, conteudo_html="<p>B</p>")
    texto = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa, conteudo_html="<p>Texto</p>")

    job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.COLECAO,
        alvo_id="colecao",
        formato=ExportJob.Formato.PDF,
        payload_json={
            "titulo": "Documento",
            "secoes": [
                {"tipo": ExportJob.AlvoTipo.RESPOSTA, "id": resposta2.id, "titulo": "Segunda"},
                {"tipo": ExportJob.AlvoTipo.TEXTO_UNICO, "id": texto.id},
                {"tipo": ExportJob.AlvoTipo.RESPOSTA, "id": resposta1.id},
            ],
        },
    )

    contexto = _build_context(job)
    conteudo = contexto.payload["conteudo_html"]

    assert "Segunda" in conteudo
    assert conteudo.index("Segunda") < conteudo.index("Texto Único")
    assert conteudo.index("Texto Único") < conteudo.index("Pergunta: Primeira")
