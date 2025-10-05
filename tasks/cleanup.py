"""Tarefas de limpeza recorrentes."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from exports.models import ExportJob


@shared_task(name="tasks.cleanup.purge_soft_deleted")
def purge_soft_deleted() -> int:
    removidos = 0
    for model in apps.get_models():
        if hasattr(model, "raw_objects") and hasattr(model, "is_deleted"):
            qs = model.raw_objects.filter(is_deleted=True)
            count = qs.count()
            if count:
                qs.delete()
                removidos += count
    return removidos


@shared_task(name="tasks.cleanup.cleanup_exports")
def cleanup_exports(dias: int = 30) -> int:
    limite = timezone.now() - timedelta(days=dias)
    antigos = ExportJob.objects.filter(finished_at__lt=limite)
    removidos = 0
    for job in antigos:
        if job.url_resultado:
            media_url = getattr(settings, "MEDIA_URL", "/media/")
            if job.url_resultado.startswith(media_url):
                relativo = job.url_resultado.replace(media_url, "", 1)
                if default_storage.exists(relativo):
                    default_storage.delete(relativo)
            job.url_resultado = ""
        job.status = ExportJob.Status.DONE
        job.save(update_fields=["url_resultado", "status"])
        removidos += 1
    return removidos
