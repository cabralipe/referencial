from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from ava.models import DiarioBordo, DiarioBordoParticipante, EncontroCurso, MatriculaCurso, PresencaCurso


def matriculas_do_curso(curso):
    return (
        MatriculaCurso.raw_objects.filter(
            curso=curso,
            cliente_id=curso.cliente_id,
            is_deleted=False,
            aluno__is_active=True,
            aluno__cliente_id=curso.cliente_id,
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


@transaction.atomic
def remover_chamada(encontro):
    """Remove a chamada, encerra o link e limpa a frequência do diário vinculado."""
    EncontroCurso.raw_objects.select_for_update().get(pk=encontro.pk)
    total = PresencaCurso.raw_objects.filter(
        encontro=encontro, is_deleted=False,
    ).update(is_deleted=True)
    encontro.dispositivos_confirmados.all().update(is_deleted=True)
    encontro.is_deleted = True
    encontro.link_aberto = False
    encontro.save(update_fields=["is_deleted", "link_aberto", "updated_at"])
    if encontro.diario_id:
        DiarioBordo.raw_objects.select_for_update().get(pk=encontro.diario_id)
        DiarioBordoParticipante.raw_objects.filter(diario_id=encontro.diario_id).update(
            presente=False, is_deleted=True,
        )
        DiarioBordo.raw_objects.filter(pk=encontro.diario_id).update(
            participantes_presentes=0, participantes_previstos=0,
        )
    return total


@transaction.atomic
def sincronizar_participantes_diario(encontro):
    """Carrega a turma sem atribuir presença antes da chamada."""
    if not encontro.diario_id:
        return
    diario = encontro.diario
    matriculas = list(matriculas_do_curso(encontro.curso))
    presencas = dict(PresencaCurso.raw_objects.filter(
        encontro=encontro, is_deleted=False,
    ).values_list("matricula_id", "presente"))
    participantes = DiarioBordoParticipante.raw_objects.filter(diario=diario)
    participantes.filter(usuario__isnull=False).exclude(
        usuario_id__in=[m.aluno_id for m in matriculas]
    ).update(is_deleted=True)
    existentes = {
        p.usuario_id: p for p in participantes.filter(usuario__isnull=False)
    }
    novos, atualizados = [], []
    for matricula in matriculas:
        participante = existentes.get(matricula.aluno_id)
        if participante is None:
            participante = DiarioBordoParticipante(
                diario=diario, cliente_id=diario.cliente_id,
                usuario_id=matricula.aluno_id, presente=False,
            )
            novos.append(participante)
        else:
            atualizados.append(participante)
        participante.nome = matricula.aluno.nome or matricula.aluno.email
        participante.identificacao = str(matricula.pk)
        participante.is_deleted = False
        if matricula.pk in presencas:
            participante.presente = presencas[matricula.pk]
    DiarioBordoParticipante.raw_objects.bulk_create(novos)
    DiarioBordoParticipante.raw_objects.bulk_update(
        atualizados, ["nome", "identificacao", "is_deleted", "presente"],
    )
    diario.frequencia_nominal = True
    diario.sincronizar_frequencia()
    DiarioBordo.raw_objects.filter(pk=diario.pk).update(
        frequencia_nominal=True, participantes_previstos=len(matriculas),
        participantes_presentes=diario.participantes_presentes,
    )


@transaction.atomic
def registrar_presenca(encontro, matricula, usuario, *, presente, origem):
    if (
        encontro.curso_id != matricula.curso_id
        or encontro.cliente_id != matricula.cliente_id
    ):
        raise ValidationError(
            "A matrícula deve pertencer ao curso e município do encontro."
        )
    if encontro.diario_id:
        # Serializa confirmações simultâneas para manter a contagem do diário.
        DiarioBordo.raw_objects.select_for_update().get(pk=encontro.diario_id)
    # Reutiliza também registros removidos para respeitar a unicidade no banco.
    resultado = PresencaCurso.raw_objects.update_or_create(
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
    if encontro.diario_id:
        participante = DiarioBordoParticipante.raw_objects.filter(
            diario_id=encontro.diario_id, usuario_id=matricula.aluno_id,
        ).first()
        dados = {
            "cliente_id": encontro.cliente_id,
            "nome": matricula.aluno.nome or matricula.aluno.email,
            "identificacao": str(matricula.pk), "presente": presente,
            "is_deleted": False,
        }
        if participante:
            DiarioBordoParticipante.raw_objects.filter(pk=participante.pk).update(**dados)
        else:
            DiarioBordoParticipante.raw_objects.create(
                diario_id=encontro.diario_id, usuario_id=matricula.aluno_id, **dados,
            )
        diario = encontro.diario
        diario.frequencia_nominal = True
        diario.sincronizar_frequencia()
        DiarioBordo.raw_objects.filter(pk=diario.pk).update(
            frequencia_nominal=True, participantes_presentes=diario.participantes_presentes,
        )
    return resultado
