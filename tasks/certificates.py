"""Tarefas de geracao de certificados fora do processo web."""

from __future__ import annotations

from celery import shared_task


@shared_task(
    name="tasks.certificates.build_certificate_pdf",
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def build_certificate_pdf(certificado_id: int, campos: list[str] | None = None) -> None:
    # Imports locais evitam carregar WeasyPrint e o dominio AVA no processo
    # que apenas publica a tarefa.
    from ava.models import Certificado
    from ava.services.certificate_service import CertificacaoService

    certificado = Certificado.raw_objects.select_related(
        "config",
        "matricula_curso__curso",
        "aluno",
    ).get(pk=certificado_id, is_deleted=False)
    if not certificado.config_id:
        raise ValueError(f"Certificado {certificado_id} sem configuracao de emissao.")

    CertificacaoService.gerar_pdf(certificado, certificado.config, campos=campos)
    certificado.save(update_fields=["arquivo_pdf"])
