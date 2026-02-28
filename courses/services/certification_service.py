"""Motor de certificacao configuravel por curso."""

from __future__ import annotations

from dataclasses import dataclass

from courses.models import (
    Curso,
    CursoCertificadoEmitido,
    CursoModulo,
    CursoParticipacao,
    CursoProgresso,
    CursoProgressoItem,
    PlanoAula,
)


@dataclass
class CertificationResult:
    checks: dict
    approved: bool
    certificate_id: int | None = None


DEFAULT_RULES = {
    "percentual_minimo_conclusao": 75,
    "numero_minimo_planos": 1,
    "presenca_obrigatoria": True,
    "entrega_final_obrigatoria": True,
    "publicacao_no_banco_obrigatoria": False,
}


def _normalized_rules(curso: Curso) -> dict:
    payload = curso.regras_certificacao_json if isinstance(curso.regras_certificacao_json, dict) else {}
    rules = dict(DEFAULT_RULES)
    for key in DEFAULT_RULES:
        if key in payload:
            rules[key] = payload[key]
    return rules


def evaluate_certification(curso: Curso, usuario_id: int, *, publicados_no_banco: int = 0) -> CertificationResult:
    rules = _normalized_rules(curso)
    progresso = CursoProgresso.objects.filter(curso=curso, usuario_id=usuario_id).first()
    percentual = int(getattr(progresso, "percentual", 0) or 0)
    participacao = CursoParticipacao.objects.filter(curso=curso, usuario_id=usuario_id).first()
    presenca = bool(getattr(participacao, "presenca_presencial", False))
    planos = PlanoAula.objects.filter(
        cliente_id=curso.cliente_id,
        curso=curso,
        autor_id=usuario_id,
        status__in=[PlanoAula.Status.EM_REVISAO, PlanoAula.Status.APROVADO, PlanoAula.Status.PUBLICADO],
    ).count()
    entrega_final = CursoProgressoItem.objects.filter(
        cliente_id=curso.cliente_id,
        progresso__curso=curso,
        progresso__usuario_id=usuario_id,
        item__modulo__tipo=CursoModulo.Tipo.ENTREGA_FINAL,
    ).exists()

    checks = {
        "percentual_minimo_conclusao": percentual >= int(rules["percentual_minimo_conclusao"]),
        "numero_minimo_planos": planos >= int(rules["numero_minimo_planos"]),
        "presenca_obrigatoria": (not bool(rules["presenca_obrigatoria"])) or presenca,
        "entrega_final_obrigatoria": (not bool(rules["entrega_final_obrigatoria"])) or entrega_final,
        "publicacao_no_banco_obrigatoria": (not bool(rules["publicacao_no_banco_obrigatoria"]))
        or publicados_no_banco > 0,
    }
    approved = all(checks.values())
    return CertificationResult(checks=checks, approved=approved)


def emit_certificate_if_eligible(
    curso: Curso,
    usuario_id: int,
    *,
    publicados_no_banco: int = 0,
    metadata: dict | None = None,
) -> CertificationResult:
    result = evaluate_certification(curso, usuario_id, publicados_no_banco=publicados_no_banco)
    if not result.approved:
        return result

    cert, _ = CursoCertificadoEmitido.objects.get_or_create(
        cliente_id=curso.cliente_id,
        curso=curso,
        usuario_id=usuario_id,
        defaults={"payload_json": metadata or {}},
    )
    result.certificate_id = cert.id
    return result

