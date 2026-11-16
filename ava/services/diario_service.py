"""Regras de negócio do Diário de Bordo."""

from __future__ import annotations

import io

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ava.models.diario import (
    DiarioBordo,
    DiarioBordoMidia,
    DiarioBordoParticipante,
    MAX_DIARIO_MIDIA_SIZE,
)
from ava.services.audit_service import AVAAuditService, diff_de_campos
from core.models import Usuario


CAMPOS_AUDITADOS = [
    "origem",
    "data_aula",
    "titulo",
    "status",
    "escola_id",
    "curso_id",
    "modulo_id",
    "aula_id",
    "professor_id",
    "participantes_presentes",
]

#: Papéis que podem revisar/bloquear registros de terceiros.
ROLES_REVISAO = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.DIRETOR,
}


class DiarioBordoService:
    """Transições de status, frequência e mídias do Diário de Bordo."""

    # -- criação/edição -------------------------------------------------
    @staticmethod
    @transaction.atomic
    def salvar(diario: DiarioBordo, usuario, *, criando: bool) -> DiarioBordo:
        diario.updated_by = usuario
        if criando:
            diario.created_by = usuario
        diario.full_clean(exclude=None)
        diario.save()
        diario.sincronizar_frequencia()
        if diario.frequencia_nominal:
            DiarioBordo.raw_objects.filter(pk=diario.pk).update(
                participantes_presentes=diario.participantes_presentes
            )
        AVAAuditService.registrar_diario(
            diario,
            usuario,
            acao="criado" if criando else "atualizado",
            diff=diff_de_campos(diario, CAMPOS_AUDITADOS),
        )
        return diario

    # -- fluxo de status ------------------------------------------------
    @staticmethod
    def pode_editar(diario: DiarioBordo, usuario) -> bool:
        if usuario.role in ROLES_REVISAO:
            return diario.status != DiarioBordo.Status.BLOQUEADO
        return diario.editavel and diario.professor_id == usuario.id

    @staticmethod
    @transaction.atomic
    def excluir(diario: DiarioBordo, usuario) -> None:
        from ava.models import EncontroCurso
        from ava.services.attendance_service import remover_chamada

        if not DiarioBordoService.pode_editar(diario, usuario):
            raise PermissionDenied("Você não pode excluir este registro. Registros bloqueados devem ser reabertos antes da exclusão.")
        encontro = EncontroCurso.raw_objects.select_for_update().filter(diario=diario).first()
        if encontro:
            remover_chamada(encontro)
        DiarioBordo.raw_objects.select_for_update().get(pk=diario.pk)
        diario.participantes.all().update(is_deleted=True, presente=False)
        diario.midias.all().update(is_deleted=True)
        diario.is_deleted = True
        diario.updated_by = usuario
        diario.participantes_presentes = 0
        diario.save(update_fields=["is_deleted", "updated_by", "participantes_presentes", "updated_at"])
        AVAAuditService.registrar_diario(diario, usuario, acao="excluido")

    @staticmethod
    @transaction.atomic
    def enviar(diario: DiarioBordo, usuario) -> DiarioBordo:
        if diario.status != DiarioBordo.Status.RASCUNHO:
            raise ValidationError("Somente rascunhos podem ser enviados.")
        if diario.professor_id != usuario.id and usuario.role not in ROLES_REVISAO:
            raise PermissionDenied("Apenas o professor responsável pode enviar o registro.")
        diario.sincronizar_frequencia()
        if diario.frequencia_nominal and diario.participantes_presentes == 0:
            raise ValidationError(
                "Registre ao menos um participante presente antes de enviar."
            )
        if not diario.frequencia_nominal and diario.participantes_presentes == 0:
            raise ValidationError(
                "Informe a quantidade de participantes presentes antes de enviar."
            )
        diario.status = DiarioBordo.Status.ENVIADO
        diario.enviado_em = timezone.now()
        diario.updated_by = usuario
        diario.save(
            update_fields=[
                "status",
                "enviado_em",
                "updated_by",
                "participantes_presentes",
                "updated_at",
            ]
        )
        AVAAuditService.registrar_diario(diario, usuario, acao="enviado")
        return diario

    @staticmethod
    @transaction.atomic
    def revisar(diario: DiarioBordo, usuario, *, parecer: str = "", bloquear: bool = False):
        if usuario.role not in ROLES_REVISAO:
            raise PermissionDenied("Você não pode revisar registros do diário de bordo.")
        if diario.status == DiarioBordo.Status.RASCUNHO:
            raise ValidationError("O registro ainda é um rascunho e não pode ser revisado.")
        diario.status = (
            DiarioBordo.Status.BLOQUEADO if bloquear else DiarioBordo.Status.REVISADO
        )
        diario.revisado_em = timezone.now()
        diario.revisado_por = usuario
        diario.parecer_revisao = parecer or ""
        diario.updated_by = usuario
        diario.save(
            update_fields=[
                "status",
                "revisado_em",
                "revisado_por",
                "parecer_revisao",
                "updated_by",
                "updated_at",
            ]
        )
        AVAAuditService.registrar_diario(
            diario,
            usuario,
            acao="bloqueado" if bloquear else "revisado",
            diff={"parecer": parecer or ""},
        )
        return diario

    @staticmethod
    @transaction.atomic
    def reabrir(diario: DiarioBordo, usuario) -> DiarioBordo:
        if usuario.role not in ROLES_REVISAO:
            raise PermissionDenied("Você não pode reabrir registros do diário de bordo.")
        diario.status = DiarioBordo.Status.RASCUNHO
        diario.enviado_em = None
        diario.updated_by = usuario
        diario.save(update_fields=["status", "enviado_em", "updated_by", "updated_at"])
        AVAAuditService.registrar_diario(diario, usuario, acao="reaberto")
        return diario

    # -- frequência -----------------------------------------------------
    @staticmethod
    @transaction.atomic
    def registrar_presenca(
        diario: DiarioBordo,
        usuario,
        *,
        nome: str,
        identificacao: str = "",
        presente: bool = True,
        justificativa: str = "",
        usuario_vinculado=None,
    ) -> DiarioBordoParticipante:
        if not DiarioBordoService.pode_editar(diario, usuario):
            raise PermissionDenied("Este registro não pode mais ser alterado.")
        participante = DiarioBordoParticipante(
            cliente_id=diario.cliente_id,
            diario=diario,
            nome=nome,
            identificacao=identificacao,
            presente=presente,
            justificativa=justificativa,
            usuario=usuario_vinculado,
        )
        participante.full_clean()
        participante.save()
        DiarioBordoService._resincronizar(diario, usuario)
        return participante

    @staticmethod
    @transaction.atomic
    def remover_presenca(diario: DiarioBordo, usuario, participante_id: int) -> None:
        if not DiarioBordoService.pode_editar(diario, usuario):
            raise PermissionDenied("Este registro não pode mais ser alterado.")
        participante = DiarioBordoParticipante.raw_objects.filter(
            is_deleted=False, diario=diario, pk=participante_id
        ).first()
        if participante is None:
            return
        participante.delete()
        DiarioBordoService._resincronizar(diario, usuario)

    @staticmethod
    def _resincronizar(diario: DiarioBordo, usuario) -> None:
        diario.sincronizar_frequencia()
        if diario.frequencia_nominal:
            DiarioBordo.raw_objects.filter(pk=diario.pk).update(
                participantes_presentes=diario.participantes_presentes
            )
        AVAAuditService.registrar_diario(
            diario,
            usuario,
            acao="frequencia_atualizada",
            diff={"presentes": diario.participantes_presentes},
        )

    # -- mídias ---------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def adicionar_midia(
        diario: DiarioBordo,
        usuario,
        arquivo,
        *,
        tipo: str = DiarioBordoMidia.Tipo.FOTO,
        legenda: str = "",
        consentimento: bool = False,
    ) -> DiarioBordoMidia:
        if not DiarioBordoService.pode_editar(diario, usuario):
            raise PermissionDenied("Este registro não pode mais receber anexos.")
        if getattr(arquivo, "size", 0) > MAX_DIARIO_MIDIA_SIZE:
            raise ValidationError({"arquivo": "O arquivo deve ter no máximo 10 MB."})

        midia = DiarioBordoMidia(
            cliente_id=diario.cliente_id,
            diario=diario,
            tipo=tipo,
            arquivo=arquivo,
            legenda=legenda,
            consentimento_registrado=consentimento,
            created_by=usuario,
            ordem=(
                DiarioBordoMidia.raw_objects.filter(
                    is_deleted=False, diario=diario
                ).count()
            ),
        )
        midia.full_clean(exclude=["nome_original", "content_type", "tamanho_bytes"])
        midia.save()
        AVAAuditService.registrar_diario(
            diario,
            usuario,
            acao="midia_adicionada",
            diff={"midia": midia.pk, "tipo": tipo, "nome": midia.nome_original},
        )
        return midia

    @staticmethod
    @transaction.atomic
    def remover_midia(diario: DiarioBordo, usuario, midia_id: int) -> None:
        if not DiarioBordoService.pode_editar(diario, usuario):
            raise PermissionDenied("Este registro não pode mais ser alterado.")
        midia = DiarioBordoMidia.raw_objects.filter(
            is_deleted=False, diario=diario, pk=midia_id
        ).first()
        if midia is None:
            return
        midia.delete()
        AVAAuditService.registrar_diario(
            diario, usuario, acao="midia_removida", diff={"midia": midia_id}
        )


class DiarioBordoExportService:
    """Exportação dos registros do diário, identificando a modalidade."""

    CABECALHOS = [
        "Data",
        "Origem",
        "Título",
        "Escola",
        "Professor",
        "Curso",
        "Módulo",
        "Aula",
        "Tipo de atividade",
        "Local",
        "Instituição",
        "Grupo participante",
        "Previstos",
        "Presentes",
        "Status",
        "Conteúdo trabalhado",
        "Metodologia",
        "Observações",
        "Fotos",
        "Criado em",
        "Município",
        "Responsável externo",
        "Modo de frequência",
        "Enviado em",
        "Revisado em",
        "Revisado por",
        "Parecer da revisão",
    ]

    @classmethod
    def montar_linhas(cls, diarios) -> list[list[str]]:
        linhas = []
        for diario in diarios:
            linhas.append(
                [
                    diario.data_aula.strftime("%d/%m/%Y") if diario.data_aula else "",
                    diario.get_origem_display(),
                    diario.titulo,
                    diario.escola.nome if diario.escola_id else "",
                    (diario.professor.nome or diario.professor.email)
                    if diario.professor_id
                    else "",
                    diario.curso.titulo if diario.curso_id else "",
                    diario.modulo.titulo if diario.modulo_id else "",
                    diario.aula.titulo if diario.aula_id else "",
                    diario.get_tipo_atividade_display() if diario.tipo_atividade else "",
                    diario.local_realizacao,
                    diario.instituicao_parceira,
                    diario.grupo_participante,
                    diario.participantes_previstos
                    if diario.participantes_previstos is not None
                    else "",
                    diario.participantes_presentes,
                    diario.get_status_display(),
                    diario.conteudo_trabalhado,
                    diario.metodologia,
                    diario.observacoes,
                    diario.midias.filter(is_deleted=False).count(),
                    diario.created_at.strftime("%d/%m/%Y %H:%M"),
                    diario.cliente.nome,
                    diario.responsavel_externo,
                    diario.get_modo_frequencia_display(),
                    diario.enviado_em.strftime("%d/%m/%Y %H:%M") if diario.enviado_em else "",
                    diario.revisado_em.strftime("%d/%m/%Y %H:%M") if diario.revisado_em else "",
                    (diario.revisado_por.nome or diario.revisado_por.email) if diario.revisado_por_id else "",
                    diario.parecer_revisao,
                ]
            )
        return linhas

    @classmethod
    def para_xlsx(cls, diarios) -> bytes:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = getattr(cls, "TITULO", "Diário de bordo")
        sheet.append(cls.CABECALHOS)
        for celula in sheet[1]:
            celula.font = Font(bold=True, color="FFFFFF")
            celula.fill = PatternFill("solid", fgColor="17365D")
        for linha in cls.montar_linhas(diarios):
            sheet.append(linha)
            for celula in sheet[sheet.max_row]:
                if isinstance(celula.value, str):
                    celula.data_type = "s"
                celula.alignment = Alignment(vertical="top", wrap_text=True)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for indice, cabecalho in enumerate(cls.CABECALHOS, start=1):
            sheet.column_dimensions[get_column_letter(indice)].width = min(
                max(len(cabecalho) + 4, 14), 45
            )
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    @classmethod
    def para_pdf(cls, diarios) -> bytes:
        from .diario_pdf import gerar_pdf

        return gerar_pdf(
            cls.CABECALHOS, cls.montar_linhas(diarios),
            frequencia=cls is DiarioBordoFrequenciaExportService,
        )

    @classmethod
    def para_csv(cls, diarios) -> bytes:
        import csv

        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        escritor.writerow(cls.CABECALHOS)
        escritor.writerows(
            ["'" + valor if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@")) else valor for valor in linha]
            for linha in cls.montar_linhas(diarios)
        )
        return buffer.getvalue().encode("utf-8-sig")


class DiarioBordoFrequenciaExportService(DiarioBordoExportService):
    """Uma linha por participante; registros sem lista mantêm os totais informados."""

    TITULO = "Frequência"
    CABECALHOS = [
        "ID do diário", "Município", "Data", "Encontro", "Escola", "Professor",
        "Curso", "Grupo participante", "Local", "Status do diário", "Modo de frequência",
        "Participante", "Identificação", "Situação", "Justificativa", "Origem da presença",
        "Previstos no encontro", "Presentes no encontro", "Ausentes registrados no encontro",
    ]

    @classmethod
    def montar_linhas(cls, diarios):
        from ava.models import EncontroCurso, PresencaCurso
        from ava.services.attendance_service import matriculas_do_curso

        linhas = []
        for diario in diarios:
            participantes = [p for p in diario.participantes.all() if not p.is_deleted]
            pessoas = {
                ("usuario", p.usuario_id) if p.usuario_id else ("nominal", p.pk):
                [p.nome, p.identificacao, "Presente" if p.presente else "Ausente", p.justificativa, "Lista nominal"]
                for p in participantes
            }
            encontro = EncontroCurso.raw_objects.filter(
                diario=diario, cliente_id=diario.cliente_id, is_deleted=False
            ).first()
            if encontro:
                presencas = {
                    p.matricula_id: p for p in PresencaCurso.raw_objects.filter(
                        encontro=encontro, cliente_id=diario.cliente_id, is_deleted=False,
                        matricula__is_deleted=False,
                    )
                }
                for matricula in matriculas_do_curso(encontro.curso):
                    p = presencas.get(matricula.pk)
                    chave = ("usuario", matricula.aluno_id)
                    if p is not None:
                        pessoas[chave] = [
                            matricula.aluno.nome or matricula.aluno.email, str(matricula.pk),
                            "Presente" if p.presente else "Ausente", "", p.get_origem_display(),
                        ]
                    elif chave not in pessoas:
                        pessoas[chave] = [matricula.aluno.nome or matricula.aluno.email, str(matricula.pk), "Não registrada", "", ""]
            nominal = diario.frequencia_nominal or encontro is not None
            presentes = sum(p[2] == "Presente" for p in pessoas.values()) if nominal else diario.participantes_presentes
            ausentes = sum(p[2] == "Ausente" for p in pessoas.values()) if nominal else ""
            previstos = diario.participantes_previstos
            if previstos is None and nominal:
                previstos = len(pessoas)
            base = [
                diario.pk, diario.cliente.nome, diario.data_aula.strftime("%d/%m/%Y"),
                diario.titulo, diario.escola.nome, diario.professor.nome or diario.professor.email,
                diario.curso.titulo if diario.curso_id else "", diario.grupo_participante,
                diario.local_realizacao, diario.get_status_display(), diario.get_modo_frequencia_display(),
            ]
            detalhes = sorted(pessoas.values(), key=lambda p: p[0].casefold())
            if not detalhes:
                detalhes = [["", "", "Sem participantes registrados" if nominal else "Somente quantidade informada", "", ""]]
            for detalhe in detalhes:
                linhas.append(base + detalhe + [previstos if previstos is not None else "", presentes, ausentes])
        return linhas
