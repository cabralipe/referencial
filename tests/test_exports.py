import pytest

from exports.models import ExportJob
from tasks.exports import build_docx, build_pdf


class DummyProvider:
    def render_pdf(self, ctx):
        return b"pdf"

    def render_docx(self, ctx):
        return b"docx"


@pytest.mark.django_db
def test_build_pdf(settings, monkeypatch, cliente, gt, tarefa):
    from curriculum.models import TextoUnico

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
    from curriculum.models import TextoUnico

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
