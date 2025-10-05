"""Tarefas Celery relacionadas a exportações."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from core.plugins import get_export_provider
from core.utils import coletar_contexto_do_cliente, obter_config
from curriculum.models import TextoUnico
from exports.models import ExportJob
from workshop.models import Quadro


@dataclass
class ExportContext:
    job: ExportJob
    payload: Dict[str, object]


def _build_context(job: ExportJob) -> ExportContext:
    cliente = job.cliente
    payload: Dict[str, object] = {
        "cliente": coletar_contexto_do_cliente(cliente),
        "titulo": f"Exportação #{job.id}",
    }
    if job.alvo_tipo == ExportJob.AlvoTipo.TEXTO_UNICO:
        texto = TextoUnico.objects.get(pk=job.alvo_id)
        payload.update(
            {
                "conteudo_html": texto.conteudo_html,
                "titulo": f"Texto Único {texto.gt.nome}",
            }
        )
    elif job.alvo_tipo == ExportJob.AlvoTipo.QUADRO:
        quadro = Quadro.objects.get(pk=job.alvo_id)
        linhas = []
        for celula in quadro.celulas.order_by("linha", "coluna"):
            linhas.append({
                "linha": celula.linha,
                "coluna": celula.coluna,
                "valor_html": celula.valor_html,
            })
        payload.update(
            {
                "conteudo_html": "<table>" + "".join(
                    f"<tr><td>{c['valor_html']}</td></tr>" for c in linhas
                ) + "</table>",
                "titulo": f"Quadro {quadro.template}",
            }
        )
    return ExportContext(job=job, payload=payload)


def enqueue_export_job(job_id: int) -> None:
    job = ExportJob.objects.get(pk=job_id)
    if job.formato == ExportJob.Formato.PDF:
        build_pdf.delay(job.id)
    else:
        build_docx.delay(job.id)


@shared_task(name="tasks.exports.build_pdf")
def build_pdf(job_id: int) -> None:
    job = ExportJob.objects.get(pk=job_id)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status"])
    try:
        context = _build_context(job)
        plugin_name = obter_config(job.cliente, "export_plugin")
        provider = get_export_provider(plugin_name)
        pdf_bytes = provider.render_pdf(context.payload)
        filename = f"exports/{job.id}.pdf"
        saved_path = default_storage.save(filename, ContentFile(pdf_bytes))
        job.url_resultado = default_storage.url(saved_path)
        job.status = ExportJob.Status.DONE
        job.finished_at = timezone.now()
        job.save(update_fields=["url_resultado", "status", "finished_at"])
    except Exception as exc:  # pragma: no cover - logging de erro
        job.status = ExportJob.Status.ERROR
        job.finished_at = timezone.now()
        job.url_resultado = ""
        job.save(update_fields=["status", "finished_at", "url_resultado"])
        raise exc


@shared_task(name="tasks.exports.build_docx")
def build_docx(job_id: int) -> None:
    job = ExportJob.objects.get(pk=job_id)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status"])
    try:
        context = _build_context(job)
        plugin_name = obter_config(job.cliente, "export_plugin")
        provider = get_export_provider(plugin_name)
        docx_bytes = provider.render_docx(context.payload)
        filename = f"exports/{job.id}.docx"
        saved_path = default_storage.save(filename, ContentFile(docx_bytes))
        job.url_resultado = default_storage.url(saved_path)
        job.status = ExportJob.Status.DONE
        job.finished_at = timezone.now()
        job.save(update_fields=["url_resultado", "status", "finished_at"])
    except Exception as exc:  # pragma: no cover
        job.status = ExportJob.Status.ERROR
        job.finished_at = timezone.now()
        job.url_resultado = ""
        job.save(update_fields=["status", "finished_at", "url_resultado"])
        raise exc
