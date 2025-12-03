"""Tarefas Celery relacionadas a exportações."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.html import escape
from django.utils import timezone

from core.plugins import get_export_provider
from core.utils import coletar_contexto_do_cliente, obter_config
from curriculum.models import Resposta, TextoUnico
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
        texto = TextoUnico.raw_objects.get(pk=job.alvo_id, cliente=cliente, is_deleted=False)
        payload.update(
            {
                "conteudo_html": texto.conteudo_html,
                "titulo": f"Texto Único {texto.gt.nome}",
            }
        )
    elif job.alvo_tipo == ExportJob.AlvoTipo.RESPOSTA:
        try:
            resposta_id = int(job.alvo_id)
        except (TypeError, ValueError):
            resposta_id = None
        resposta = (
            Resposta.raw_objects.select_related("pergunta", "gt")
            .filter(pk=resposta_id, cliente=cliente)
            .first()
        )
        pergunta_texto = getattr(getattr(resposta, "pergunta", None), "texto", "") if resposta else ""
        titulo = (
            job.payload_json.get("titulo")  # type: ignore[attr-defined]
            or (f"Pergunta: {pergunta_texto[:120]}" if pergunta_texto else f"Resposta #{job.alvo_id}")
        )
        corpo = getattr(resposta, "conteudo_html", "") or "<p>Sem conteúdo disponível.</p>"
        payload.update({"conteudo_html": f"<section><h2>{escape(titulo)}</h2>{corpo}</section>", "titulo": titulo})
    elif job.alvo_tipo == ExportJob.AlvoTipo.QUADRO:
        quadro = Quadro.raw_objects.get(pk=job.alvo_id, cliente=cliente, is_deleted=False)
        linhas: Dict[int, list[str]] = {}
        for celula in quadro.celulas.order_by("linha", "coluna"):
            linhas.setdefault(celula.linha, []).append(celula.valor_html)

        table_rows = []
        for linha_idx in sorted(linhas.keys()):
            colunas = linhas[linha_idx]
            cells_html = "".join(f"<td>{valor}</td>" for valor in colunas)
            table_rows.append(f"<tr>{cells_html}</tr>")

        conteudo_html = "<table><tbody>" + "".join(table_rows) + "</tbody></table>"
        payload.update(
            {
                "conteudo_html": conteudo_html,
                "titulo": f"Quadro {quadro.template}",
            }
        )
    elif job.alvo_tipo == ExportJob.AlvoTipo.COLECAO:
        secoes = job.payload_json.get("secoes") if isinstance(job.payload_json, dict) else []
        if not isinstance(secoes, Iterable):
            secoes = []

        def _secao_get(obj: object, key: str, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        resposta_ids: List[int] = []
        texto_ids: List[int] = []
        for secao in secoes or []:
            tipo = _secao_get(secao, "tipo")
            try:
                alvo_id = int(_secao_get(secao, "id", 0))
            except (TypeError, ValueError):
                continue
            if tipo == ExportJob.AlvoTipo.RESPOSTA:
                resposta_ids.append(alvo_id)
            elif tipo == ExportJob.AlvoTipo.TEXTO_UNICO:
                texto_ids.append(alvo_id)

        respostas = Resposta.raw_objects.select_related("pergunta", "gt").filter(
            pk__in=resposta_ids, cliente=cliente
        )
        respostas_map = {item.pk: item for item in respostas}
        textos = TextoUnico.raw_objects.select_related("gt").filter(pk__in=texto_ids, cliente=cliente, is_deleted=False)
        textos_map = {item.pk: item for item in textos}

        blocos: List[str] = []
        for secao in secoes or []:
            secao_tipo = _secao_get(secao, "tipo")
            try:
                secao_id = int(_secao_get(secao, "id", 0))
            except (TypeError, ValueError):
                continue
            secao_titulo = _secao_get(secao, "titulo")
            if secao_tipo == ExportJob.AlvoTipo.RESPOSTA:
                resposta = respostas_map.get(secao_id)
                if not resposta:
                    continue
                pergunta_texto = getattr(getattr(resposta, "pergunta", None), "texto", "") or ""
                titulo = secao_titulo or (f"Pergunta: {pergunta_texto[:120]}" if pergunta_texto else f"Resposta #{secao_id}")
                corpo = resposta.conteudo_html or "<p>Sem conteúdo disponível.</p>"
                blocos.append(f"<section><h2>{escape(titulo)}</h2>{corpo}</section>")
            elif secao_tipo == ExportJob.AlvoTipo.TEXTO_UNICO:
                texto = textos_map.get(secao_id)
                if not texto:
                    continue
                gt_nome = getattr(getattr(texto, "gt", None), "nome", None)
                titulo = secao_titulo or f"Texto Único {gt_nome or ''} #{secao_id}"
                corpo = texto.conteudo_html or "<p>Sem conteúdo disponível.</p>"
                blocos.append(f"<section><h2>{escape(titulo)}</h2>{corpo}</section>")

        payload.update(
            {
                "conteudo_html": "".join(blocos) or "<p>Nenhum conteúdo encontrado para esta coleção.</p>",
                "titulo": job.payload_json.get("titulo")  # type: ignore[attr-defined]
                or f"Exportação #{job.id}",
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
