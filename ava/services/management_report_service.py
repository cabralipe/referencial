from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q
from django.utils import timezone

from ava.models import (
    Atividade,
    AtividadeForumMensagem,
    AtividadeTentativa,
    Aula,
    ConteudoAula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    ProgressoConteudo,
    ProgressoModulo,
)
from exports.services.pdf import html_to_pdf_bytes

try:  # pragma: no cover - dependencia validada pelo ambiente
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:  # pragma: no cover - fallback defensivo
    Workbook = None  # type: ignore[assignment]
    Alignment = Font = PatternFill = None  # type: ignore[assignment]


class AVAManagementReportService:
    STATUS_LABELS = dict(AtividadeTentativa.Status.choices)
    TIPO_LABELS = dict(Atividade.Tipo.choices)

    @staticmethod
    def _is_super_admin(user) -> bool:
        return getattr(user, "role", None) == get_user_model().Role.SUPER_ADMIN

    @staticmethod
    def _display_user(usuario) -> str:
        return getattr(usuario, "nome", "") or usuario.get_full_name() or usuario.email

    @staticmethod
    def _to_local_datetime(value):
        if value is None:
            return None
        return timezone.localtime(value)

    @classmethod
    def _excel_datetime(cls, value):
        value = cls._to_local_datetime(value)
        if value is None:
            return None
        return value.replace(tzinfo=None)

    @classmethod
    def _merge_datetimes(cls, *values):
        validos = [cls._to_local_datetime(value) for value in values if value]
        if not validos:
            return None
        return max(validos)

    @classmethod
    def _scoped_user_queryset(cls, user):
        qs = get_user_model().objects.all()
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)
        return qs

    @classmethod
    def _scoped_course_queryset(cls, user):
        qs = Curso.objects.all()
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)
        return qs

    @classmethod
    def _scoped_module_queryset(cls, user):
        qs = CursoModulo.objects.select_related("curso")
        if not cls._is_super_admin(user):
            qs = qs.filter(curso__cliente_id=user.cliente_id)
        return qs

    @classmethod
    def _scoped_lesson_queryset(cls, user):
        qs = Aula.objects.select_related("modulo", "modulo__curso")
        if not cls._is_super_admin(user):
            qs = qs.filter(modulo__curso__cliente_id=user.cliente_id)
        return qs

    @classmethod
    def _resolve_course_ids(cls, user, filtros) -> list[int] | None:
        if filtros.get("curso_id"):
            return [filtros["curso_id"]]
        if filtros.get("modulo_id"):
            return list(
                cls._scoped_module_queryset(user)
                .filter(id=filtros["modulo_id"])
                .values_list("curso_id", flat=True)[:1]
            )
        if filtros.get("aula_id"):
            return list(
                cls._scoped_lesson_queryset(user)
                .filter(id=filtros["aula_id"])
                .values_list("modulo__curso_id", flat=True)[:1]
            )
        return None

    @classmethod
    def _matriculas_queryset(cls, user, filtros):
        qs = MatriculaCurso.objects.select_related("aluno", "curso")
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)

        course_ids = cls._resolve_course_ids(user, filtros)
        if course_ids is not None:
            qs = qs.filter(curso_id__in=course_ids) if course_ids else qs.none()

        if filtros.get("usuario_id"):
            qs = qs.filter(aluno_id=filtros["usuario_id"])

        if filtros.get("q"):
            termo = filtros["q"]
            qs = qs.filter(
                Q(aluno__nome__icontains=termo)
                | Q(aluno__email__icontains=termo)
                | Q(curso__titulo__icontains=termo)
            )

        return qs.order_by("curso__titulo", "aluno__nome", "aluno__email")

    @classmethod
    def _tentativas_queryset(cls, user, filtros):
        qs = AtividadeTentativa.objects.select_related(
            "aluno",
            "atividade__aula__modulo__curso",
        )
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)

        if filtros.get("usuario_id"):
            qs = qs.filter(aluno_id=filtros["usuario_id"])
        if filtros.get("curso_id"):
            qs = qs.filter(atividade__aula__modulo__curso_id=filtros["curso_id"])
        if filtros.get("modulo_id"):
            qs = qs.filter(atividade__aula__modulo_id=filtros["modulo_id"])
        if filtros.get("aula_id"):
            qs = qs.filter(atividade__aula_id=filtros["aula_id"])
        if filtros.get("status"):
            qs = qs.filter(status=filtros["status"])
        if filtros.get("tipo"):
            qs = qs.filter(atividade__tipo=filtros["tipo"])
        if filtros.get("data_inicio"):
            qs = qs.filter(data_inicio__date__gte=filtros["data_inicio"])
        if filtros.get("data_fim"):
            qs = qs.filter(data_inicio__date__lte=filtros["data_fim"])
        if filtros.get("q"):
            termo = filtros["q"]
            qs = qs.filter(
                Q(aluno__nome__icontains=termo)
                | Q(aluno__email__icontains=termo)
                | Q(atividade__titulo__icontains=termo)
                | Q(atividade__aula__titulo__icontains=termo)
                | Q(atividade__aula__modulo__titulo__icontains=termo)
                | Q(atividade__aula__modulo__curso__titulo__icontains=termo)
            )
        return qs

    @classmethod
    def _forum_queryset(cls, user, filtros):
        if filtros.get("tipo") and filtros["tipo"] != Atividade.Tipo.FORUM:
            return AtividadeForumMensagem.objects.none()

        qs = AtividadeForumMensagem.objects.select_related(
            "autor",
            "atividade__aula__modulo__curso",
            "resposta_para",
        )
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)

        if filtros.get("usuario_id"):
            qs = qs.filter(autor_id=filtros["usuario_id"])
        if filtros.get("curso_id"):
            qs = qs.filter(atividade__aula__modulo__curso_id=filtros["curso_id"])
        if filtros.get("modulo_id"):
            qs = qs.filter(atividade__aula__modulo_id=filtros["modulo_id"])
        if filtros.get("aula_id"):
            qs = qs.filter(atividade__aula_id=filtros["aula_id"])
        if filtros.get("data_inicio"):
            qs = qs.filter(created_at__date__gte=filtros["data_inicio"])
        if filtros.get("data_fim"):
            qs = qs.filter(created_at__date__lte=filtros["data_fim"])
        if filtros.get("q"):
            termo = filtros["q"]
            qs = qs.filter(
                Q(autor__nome__icontains=termo)
                | Q(autor__email__icontains=termo)
                | Q(texto__icontains=termo)
                | Q(atividade__titulo__icontains=termo)
                | Q(atividade__aula__titulo__icontains=termo)
                | Q(atividade__aula__modulo__titulo__icontains=termo)
                | Q(atividade__aula__modulo__curso__titulo__icontains=termo)
            )
        return qs

    @classmethod
    def _content_queryset(cls, user, filtros):
        qs = ProgressoConteudo.objects.select_related(
            "progresso_aula__matricula__aluno",
            "conteudo__aula__modulo__curso",
        ).filter(is_visualizado=True)
        if not cls._is_super_admin(user):
            qs = qs.filter(cliente_id=user.cliente_id)

        if filtros.get("usuario_id"):
            qs = qs.filter(progresso_aula__matricula__aluno_id=filtros["usuario_id"])
        if filtros.get("curso_id"):
            qs = qs.filter(conteudo__aula__modulo__curso_id=filtros["curso_id"])
        if filtros.get("modulo_id"):
            qs = qs.filter(conteudo__aula__modulo_id=filtros["modulo_id"])
        if filtros.get("aula_id"):
            qs = qs.filter(conteudo__aula_id=filtros["aula_id"])
        if filtros.get("data_inicio"):
            qs = qs.filter(data_visualizacao__date__gte=filtros["data_inicio"])
        if filtros.get("data_fim"):
            qs = qs.filter(data_visualizacao__date__lte=filtros["data_fim"])
        if filtros.get("q"):
            termo = filtros["q"]
            qs = qs.filter(
                Q(progresso_aula__matricula__aluno__nome__icontains=termo)
                | Q(progresso_aula__matricula__aluno__email__icontains=termo)
                | Q(conteudo__titulo__icontains=termo)
                | Q(conteudo__aula__titulo__icontains=termo)
                | Q(conteudo__aula__modulo__titulo__icontains=termo)
                | Q(conteudo__aula__modulo__curso__titulo__icontains=termo)
            )
        return qs

    @classmethod
    def _selected_objects(cls, user, filtros) -> dict[str, Any]:
        usuario = None
        curso = None
        modulo = None
        aula = None

        if filtros.get("usuario_id"):
            usuario = cls._scoped_user_queryset(user).filter(id=filtros["usuario_id"]).first()
        if filtros.get("curso_id"):
            curso = cls._scoped_course_queryset(user).filter(id=filtros["curso_id"]).first()
        if filtros.get("modulo_id"):
            modulo = cls._scoped_module_queryset(user).filter(id=filtros["modulo_id"]).first()
        if filtros.get("aula_id"):
            aula = cls._scoped_lesson_queryset(user).filter(id=filtros["aula_id"]).first()

        return {
            "usuario": usuario,
            "curso": curso,
            "modulo": modulo,
            "aula": aula,
        }

    @classmethod
    def _filter_labels(cls, user, filtros, selected):
        labels = []
        if filtros.get("q"):
            labels.append(f'Busca: "{filtros["q"]}"')
        if selected["usuario"]:
            labels.append(f"Usuario: {cls._display_user(selected['usuario'])}")
        if selected["curso"]:
            labels.append(f"Curso: {selected['curso'].titulo}")
        if selected["modulo"]:
            labels.append(f"Modulo: {selected['modulo'].titulo}")
        if selected["aula"]:
            labels.append(f"Aula: {selected['aula'].titulo}")
        if filtros.get("status"):
            labels.append(f"Status da tentativa: {cls.STATUS_LABELS.get(filtros['status'], filtros['status'])}")
        if filtros.get("tipo"):
            labels.append(f"Tipo de atividade: {cls.TIPO_LABELS.get(filtros['tipo'], filtros['tipo'])}")
        if filtros.get("data_inicio"):
            labels.append(f"Interacoes a partir de: {filtros['data_inicio'].strftime('%d/%m/%Y')}")
        if filtros.get("data_fim"):
            labels.append(f"Interacoes ate: {filtros['data_fim'].strftime('%d/%m/%Y')}")
        if not labels:
            labels.append("Sem filtros adicionais. Relatorio considera o escopo completo da gestao.")
        return labels

    @classmethod
    def build_report(cls, user, filtros) -> dict[str, Any]:
        selected = cls._selected_objects(user, filtros)
        matriculas = list(cls._matriculas_queryset(user, filtros))
        matricula_ids = [matricula.id for matricula in matriculas]
        curso_ids = sorted({matricula.curso_id for matricula in matriculas})
        matricula_by_key = {(matricula.aluno_id, matricula.curso_id): matricula for matricula in matriculas}

        modulos_por_curso = defaultdict(list)
        if curso_ids:
            for modulo in CursoModulo.objects.filter(curso_id__in=curso_ids, is_active=True).order_by("curso_id", "ordem", "id"):
                modulos_por_curso[modulo.curso_id].append(modulo)

        progresso_modulos = {}
        if matricula_ids:
            progresso_modulos = {
                (progresso.matricula_id, progresso.modulo_id): progresso
                for progresso in ProgressoModulo.objects.filter(matricula_id__in=matricula_ids).select_related("modulo")
            }

        tentativas_stats = {}
        for item in cls._tentativas_queryset(user, filtros).values(
            "aluno_id",
            "atividade__aula__modulo__curso_id",
        ).annotate(
            envios_atividade=Count(
                "id",
                filter=Q(status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA]),
            ),
            atividades_corrigidas=Count("id", filter=Q(status=AtividadeTentativa.Status.CORRIGIDA)),
            envios_com_anexo=Count("id", filter=Q(arquivo_enviado__isnull=False) & ~Q(arquivo_enviado="")),
            ultima_tentativa=Max("data_envio"),
        ):
            tentativas_stats[(item["aluno_id"], item["atividade__aula__modulo__curso_id"])] = item

        forum_stats = {}
        for item in cls._forum_queryset(user, filtros).values(
            "autor_id",
            "atividade__aula__modulo__curso_id",
        ).annotate(
            mensagens_forum=Count("id"),
            respostas_forum=Count("id", filter=Q(resposta_para__isnull=False)),
            ultima_mensagem=Max("created_at"),
        ):
            forum_stats[(item["autor_id"], item["atividade__aula__modulo__curso_id"])] = item

        conteudo_stats = {}
        for item in cls._content_queryset(user, filtros).values("progresso_aula__matricula_id").annotate(
            conteudos_visualizados=Count("id"),
            ultima_visualizacao=Max("data_visualizacao"),
        ):
            conteudo_stats[item["progresso_aula__matricula_id"]] = item

        linhas = []
        for matricula in matriculas:
            key = (matricula.aluno_id, matricula.curso_id)
            tentativas = tentativas_stats.get(key, {})
            forum = forum_stats.get(key, {})
            conteudos = conteudo_stats.get(matricula.id, {})

            concluidos = []
            pendentes = []
            for modulo in modulos_por_curso.get(matricula.curso_id, []):
                progresso = progresso_modulos.get((matricula.id, modulo.id))
                percentual = progresso.percentual if progresso else 0
                if progresso and progresso.is_concluido:
                    concluidos.append(modulo.titulo)
                else:
                    pendentes.append(modulo.titulo if percentual == 0 else f"{modulo.titulo} ({percentual}%)")

            ultima_interacao = cls._merge_datetimes(
                tentativas.get("ultima_tentativa"),
                forum.get("ultima_mensagem"),
                conteudos.get("ultima_visualizacao"),
            )

            linha = {
                "aluno_nome": cls._display_user(matricula.aluno),
                "aluno_email": matricula.aluno.email,
                "curso_titulo": matricula.curso.titulo,
                "status": matricula.status,
                "status_label": matricula.get_status_display(),
                "progresso_percentual": matricula.progresso_percentual,
                "modulos_total": len(modulos_por_curso.get(matricula.curso_id, [])),
                "modulos_concluidos": len(concluidos),
                "modulos_pendentes": len(pendentes),
                "lista_modulos_concluidos": concluidos,
                "lista_modulos_pendentes": pendentes,
                "envios_atividade": tentativas.get("envios_atividade", 0) or 0,
                "atividades_corrigidas": tentativas.get("atividades_corrigidas", 0) or 0,
                "envios_com_anexo": tentativas.get("envios_com_anexo", 0) or 0,
                "mensagens_forum": forum.get("mensagens_forum", 0) or 0,
                "respostas_forum": forum.get("respostas_forum", 0) or 0,
                "conteudos_visualizados": conteudos.get("conteudos_visualizados", 0) or 0,
                "ultima_interacao": ultima_interacao,
                "data_matricula": cls._to_local_datetime(matricula.data_matricula),
                "data_conclusao": cls._to_local_datetime(matricula.data_conclusao),
            }
            linha["total_interacoes"] = (
                linha["envios_atividade"] + linha["mensagens_forum"] + linha["conteudos_visualizados"]
            )
            linhas.append(linha)

        top_interacao = sorted(
            linhas,
            key=lambda item: (
                item["total_interacoes"],
                item["mensagens_forum"],
                item["envios_atividade"],
                item["conteudos_visualizados"],
                item["progresso_percentual"],
            ),
            reverse=True,
        )
        pendentes = sorted(
            [linha for linha in linhas if linha["status"] != MatriculaCurso.Status.CONCLUIDA],
            key=lambda item: (
                item["progresso_percentual"],
                item["total_interacoes"],
                item["aluno_nome"].lower(),
            ),
        )

        total_alunos_unicos = len({linha["aluno_email"] for linha in linhas})
        concluidos_total = sum(1 for linha in linhas if linha["status"] == MatriculaCurso.Status.CONCLUIDA)
        progresso_medio = round(
            sum(linha["progresso_percentual"] for linha in linhas) / len(linhas),
            1,
        ) if linhas else 0.0

        escopo = "Todos os cursos do AVA"
        if selected["aula"]:
            escopo = f"Aula {selected['aula'].titulo}"
        elif selected["modulo"]:
            escopo = f"Modulo {selected['modulo'].titulo}"
        elif selected["curso"]:
            escopo = f"Curso {selected['curso'].titulo}"

        return {
            "generated_at": timezone.localtime(),
            "cliente_label": getattr(getattr(user, "cliente", None), "nome", "") or "Visao global",
            "escopo_label": escopo,
            "applied_filters": cls._filter_labels(user, filtros, selected),
            "linhas": linhas,
            "top_interacao": top_interacao,
            "pendentes": pendentes,
            "metricas": {
                "total_alunos_unicos": total_alunos_unicos,
                "total_matriculas": len(linhas),
                "concluidos": concluidos_total,
                "pendentes": len(linhas) - concluidos_total,
                "taxa_conclusao": round((concluidos_total / len(linhas)) * 100, 1) if linhas else 0.0,
                "progresso_medio": progresso_medio,
                "envios_atividade": sum(linha["envios_atividade"] for linha in linhas),
                "mensagens_forum": sum(linha["mensagens_forum"] for linha in linhas),
                "conteudos_visualizados": sum(linha["conteudos_visualizados"] for linha in linhas),
                "sem_interacao": sum(1 for linha in linhas if linha["total_interacoes"] == 0),
                "ultima_interacao_geral": cls._merge_datetimes(
                    *(linha["ultima_interacao"] for linha in linhas if linha["ultima_interacao"])
                ),
            },
        }

    @classmethod
    def render_pdf_bytes(cls, report_data: dict[str, Any]) -> bytes:
        context = {
            "titulo": "Relatorio nominal de progresso e interacoes do AVA",
            **report_data,
            "top_interacao": report_data["top_interacao"][:10],
        }
        return html_to_pdf_bytes("ava/management/dashboard_report_pdf.html", context)

    @classmethod
    def render_xlsx_bytes(cls, report_data: dict[str, Any]) -> bytes:
        if Workbook is None:
            raise RuntimeError("openpyxl nao esta disponivel no ambiente.")

        workbook = Workbook()
        resumo = workbook.active
        resumo.title = "Resumo"

        cabecalho_fill = PatternFill("solid", fgColor="1D4ED8")
        cabecalho_font = Font(color="FFFFFF", bold=True)
        titulo_font = Font(size=16, bold=True)
        destaque_font = Font(size=12, bold=True)
        wrap_alignment = Alignment(wrap_text=True, vertical="top")

        resumo["A1"] = "Relatorio nominal de progresso e interacoes do AVA"
        resumo["A1"].font = titulo_font
        resumo["A3"] = "Gerado em"
        resumo["B3"] = cls._excel_datetime(report_data["generated_at"])
        resumo["B3"].number_format = "dd/mm/yyyy hh:mm"
        resumo["A4"] = "Cliente"
        resumo["B4"] = report_data["cliente_label"]
        resumo["A5"] = "Escopo"
        resumo["B5"] = report_data["escopo_label"]

        resumo["A7"] = "Filtros aplicados"
        resumo["A7"].font = destaque_font
        for indice, filtro in enumerate(report_data["applied_filters"], start=8):
            resumo[f"A{indice}"] = filtro

        metricas_inicio = 8 + len(report_data["applied_filters"]) + 2
        resumo[f"A{metricas_inicio}"] = "Indicador"
        resumo[f"B{metricas_inicio}"] = "Valor"
        for coluna in ("A", "B"):
            resumo[f"{coluna}{metricas_inicio}"].fill = cabecalho_fill
            resumo[f"{coluna}{metricas_inicio}"].font = cabecalho_font

        metricas_labels = [
            ("Alunos unicos", report_data["metricas"]["total_alunos_unicos"]),
            ("Matriculas no relatorio", report_data["metricas"]["total_matriculas"]),
            ("Matriculas concluidas", report_data["metricas"]["concluidos"]),
            ("Matriculas pendentes", report_data["metricas"]["pendentes"]),
            ("Taxa de conclusao (%)", report_data["metricas"]["taxa_conclusao"]),
            ("Progresso medio (%)", report_data["metricas"]["progresso_medio"]),
            ("Envios de atividade", report_data["metricas"]["envios_atividade"]),
            ("Mensagens no forum", report_data["metricas"]["mensagens_forum"]),
            ("Conteudos visualizados", report_data["metricas"]["conteudos_visualizados"]),
            ("Alunos sem interacao", report_data["metricas"]["sem_interacao"]),
        ]
        for linha_indice, (label, valor) in enumerate(metricas_labels, start=metricas_inicio + 1):
            resumo[f"A{linha_indice}"] = label
            resumo[f"B{linha_indice}"] = valor

        resumo.column_dimensions["A"].width = 28
        resumo.column_dimensions["B"].width = 24

        alunos_sheet = workbook.create_sheet("Alunos")
        headers = [
            "Aluno",
            "E-mail",
            "Curso",
            "Status da matricula",
            "Progresso (%)",
            "Modulos concluidos",
            "Modulos pendentes",
            "Lista de modulos concluidos",
            "Lista de modulos pendentes",
            "Envios de atividade",
            "Atividades corrigidas",
            "Envios com anexo",
            "Mensagens no forum",
            "Respostas no forum",
            "Conteudos visualizados",
            "Total de interacoes",
            "Ultima interacao",
            "Data da matricula",
            "Data de conclusao",
        ]
        alunos_sheet.append(headers)
        for cell in alunos_sheet[1]:
            cell.fill = cabecalho_fill
            cell.font = cabecalho_font

        for linha in report_data["linhas"]:
            alunos_sheet.append(
                [
                    linha["aluno_nome"],
                    linha["aluno_email"],
                    linha["curso_titulo"],
                    linha["status_label"],
                    linha["progresso_percentual"],
                    linha["modulos_concluidos"],
                    linha["modulos_pendentes"],
                    ", ".join(linha["lista_modulos_concluidos"]) or "-",
                    ", ".join(linha["lista_modulos_pendentes"]) or "-",
                    linha["envios_atividade"],
                    linha["atividades_corrigidas"],
                    linha["envios_com_anexo"],
                    linha["mensagens_forum"],
                    linha["respostas_forum"],
                    linha["conteudos_visualizados"],
                    linha["total_interacoes"],
                    cls._excel_datetime(linha["ultima_interacao"]),
                    cls._excel_datetime(linha["data_matricula"]),
                    cls._excel_datetime(linha["data_conclusao"]),
                ]
            )

        for row in alunos_sheet.iter_rows(min_row=2):
            row[7].alignment = wrap_alignment
            row[8].alignment = wrap_alignment
            for idx in (16, 17, 18):
                if row[idx].value:
                    row[idx].number_format = "dd/mm/yyyy hh:mm"

        alunos_sheet.freeze_panes = "A2"
        alunos_sheet.auto_filter.ref = alunos_sheet.dimensions
        larguras = {
            "A": 24,
            "B": 28,
            "C": 28,
            "D": 20,
            "E": 14,
            "F": 18,
            "G": 18,
            "H": 40,
            "I": 40,
            "J": 18,
            "K": 18,
            "L": 18,
            "M": 18,
            "N": 18,
            "O": 20,
            "P": 18,
            "Q": 18,
            "R": 18,
            "S": 18,
        }
        for coluna, largura in larguras.items():
            alunos_sheet.column_dimensions[coluna].width = largura

        top_sheet = workbook.create_sheet("Top interacao")
        top_headers = [
            "Aluno",
            "Curso",
            "Total de interacoes",
            "Envios de atividade",
            "Mensagens no forum",
            "Conteudos visualizados",
            "Ultima interacao",
        ]
        top_sheet.append(top_headers)
        for cell in top_sheet[1]:
            cell.fill = cabecalho_fill
            cell.font = cabecalho_font
        for linha in report_data["top_interacao"]:
            top_sheet.append(
                [
                    linha["aluno_nome"],
                    linha["curso_titulo"],
                    linha["total_interacoes"],
                    linha["envios_atividade"],
                    linha["mensagens_forum"],
                    linha["conteudos_visualizados"],
                    cls._excel_datetime(linha["ultima_interacao"]),
                ]
            )
        for row in top_sheet.iter_rows(min_row=2):
            if row[6].value:
                row[6].number_format = "dd/mm/yyyy hh:mm"
        for coluna, largura in {"A": 24, "B": 28, "C": 18, "D": 18, "E": 18, "F": 20, "G": 18}.items():
            top_sheet.column_dimensions[coluna].width = largura

        pendentes_sheet = workbook.create_sheet("Pendentes")
        pendentes_headers = [
            "Aluno",
            "Curso",
            "Status da matricula",
            "Progresso (%)",
            "Modulos pendentes",
            "Lista de modulos pendentes",
            "Envios de atividade",
            "Mensagens no forum",
            "Ultima interacao",
        ]
        pendentes_sheet.append(pendentes_headers)
        for cell in pendentes_sheet[1]:
            cell.fill = cabecalho_fill
            cell.font = cabecalho_font
        for linha in report_data["pendentes"]:
            pendentes_sheet.append(
                [
                    linha["aluno_nome"],
                    linha["curso_titulo"],
                    linha["status_label"],
                    linha["progresso_percentual"],
                    linha["modulos_pendentes"],
                    ", ".join(linha["lista_modulos_pendentes"]) or "-",
                    linha["envios_atividade"],
                    linha["mensagens_forum"],
                    cls._excel_datetime(linha["ultima_interacao"]),
                ]
            )
        for row in pendentes_sheet.iter_rows(min_row=2):
            row[5].alignment = wrap_alignment
            if row[8].value:
                row[8].number_format = "dd/mm/yyyy hh:mm"
        for coluna, largura in {"A": 24, "B": 28, "C": 20, "D": 14, "E": 18, "F": 40, "G": 18, "H": 18, "I": 18}.items():
            pendentes_sheet.column_dimensions[coluna].width = largura

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer.read()
