from decimal import Decimal

from django.core.exceptions import ValidationError

from ava.models import EncontroCurso, MatriculaCurso, PresencaCurso


def matriculas_do_curso(curso):
    return (
        MatriculaCurso.raw_objects.filter(
            curso=curso,
            cliente_id=curso.cliente_id,
            is_deleted=False,
            aluno__is_active=True,
            status__in=[MatriculaCurso.Status.ATIVA, MatriculaCurso.Status.CONCLUIDA],
        )
        .select_related("aluno")
        .order_by("aluno__nome", "id")
    )


def resumo_frequencia(matricula):
    encontros = EncontroCurso.raw_objects.filter(
        curso_id=matricula.curso_id,
        cliente_id=matricula.cliente_id,
        is_deleted=False,
        realizado=True,
    )
    total = encontros.count()
    presentes = PresencaCurso.raw_objects.filter(
        encontro__in=encontros,
        matricula=matricula,
        cliente_id=matricula.cliente_id,
        presente=True,
        is_deleted=False,
    ).count()
    percentual = Decimal(presentes * 100) / Decimal(total) if total else Decimal(0)
    return {"total": total, "presentes": presentes, "percentual": percentual}


def registrar_presenca(encontro, matricula, usuario, *, presente, origem):
    if (
        encontro.curso_id != matricula.curso_id
        or encontro.cliente_id != matricula.cliente_id
    ):
        raise ValidationError(
            "A matrícula deve pertencer ao curso e município do encontro."
        )
    # Reutiliza também registros removidos para respeitar a unicidade no banco.
    return PresencaCurso.raw_objects.update_or_create(
        encontro=encontro,
        matricula=matricula,
        defaults={
            "cliente_id": encontro.cliente_id,
            "presente": presente,
            "registrado_por": usuario,
            "origem": origem,
            "is_deleted": False,
        },
    )
