import pytest

from curriculum.models import Resposta, TextoUnico
from tasks.exports import enqueue_export_job
from tasks.synthesis import generate_texto_unico


@pytest.mark.django_db
def test_generate_texto_unico_task(cliente, gt, tarefa, pergunta, usuario):
    Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Conteúdo GT</p>",
        autor=usuario,
    )
    texto = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa, responsavel=usuario)

    result = generate_texto_unico(texto.id)

    texto.refresh_from_db()
    assert result == texto.id
    assert "Conteúdo GT" in texto.conteudo_html


@pytest.mark.django_db
def test_enqueue_export_job_routes(monkeypatch, cliente, gt, tarefa):
    from exports.models import ExportJob
    from curriculum.models import TextoUnico

    texto = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa)
    pdf_job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.TEXTO_UNICO,
        alvo_id=str(texto.id),
        formato=ExportJob.Formato.PDF,
    )
    docx_job = ExportJob.objects.create(
        cliente=cliente,
        alvo_tipo=ExportJob.AlvoTipo.TEXTO_UNICO,
        alvo_id=str(texto.id),
        formato=ExportJob.Formato.DOCX,
    )

    called = {"pdf": None, "docx": None}

    monkeypatch.setattr("tasks.exports.build_pdf.delay", lambda job_id: called.__setitem__("pdf", job_id))
    monkeypatch.setattr("tasks.exports.build_docx.delay", lambda job_id: called.__setitem__("docx", job_id))

    enqueue_export_job(pdf_job.id)
    enqueue_export_job(docx_job.id)

    assert called["pdf"] == pdf_job.id
    assert called["docx"] == docx_job.id
