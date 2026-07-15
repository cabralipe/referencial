from __future__ import annotations

from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.db.models import Avg, Count, Max, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from ava.forms import AtividadeTentativaCorrecaoForm
from ava.models import (
    Atividade,
    AtividadeForumAnexo,
    AtividadeForumMensagem,
    AtividadeTentativa,
    AtividadeTentativaArquivo,
    Aula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    QuizQuestao,
    QuizRespostaItem,
)
from ava.services import AVAManagementReportService, AtividadeService
from core.models import Eixo, Usuario
from core.threadlocals import cliente_scope
from curriculum.models import Escola


ALLOWED_AVA_MANAGEMENT_ROLES = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.ARTICULADOR,
    Usuario.Role.REVISOR,
    Usuario.Role.SUPER_ADMIN,
}


def _parse_int(raw_value: str | None) -> int | None:
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _parse_date(raw_value: str | None) -> date | None:
    if raw_value in (None, ""):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _extract_dashboard_filters(request):
    data_inicio_raw = request.GET.get("data_inicio", "").strip()
    data_fim_raw = request.GET.get("data_fim", "").strip()
    filtros = {
        "q": request.GET.get("q", "").strip(),
        "cliente_id": _parse_int(request.GET.get("municipio")),
        "escola_id": _parse_int(request.GET.get("escola")),
        "usuario_id": _parse_int(request.GET.get("usuario")),
        "curso_id": _parse_int(request.GET.get("curso")),
        "modulo_id": _parse_int(request.GET.get("modulo")),
        "aula_id": _parse_int(request.GET.get("aula")),
        "eixo_id": _parse_int(request.GET.get("eixo")),
        "status": request.GET.get("status", "").strip(),
        "tipo": request.GET.get("tipo", "").strip(),
        "data_inicio": _parse_date(data_inicio_raw),
        "data_fim": _parse_date(data_fim_raw),
    }
    return filtros, data_inicio_raw, data_fim_raw


def ava_management_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(request.user, "role", None) not in ALLOWED_AVA_MANAGEMENT_ROLES:
            raise PermissionDenied("Você não possui permissão para acessar a gestão do AVA.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _is_super_admin(user) -> bool:
    return getattr(user, "role", None) == Usuario.Role.SUPER_ADMIN


def _ava_cliente_ids(user, cliente_id=None) -> list[int]:
    permitidos = user.get_ava_clientes_queryset()
    if cliente_id and permitidos.filter(pk=cliente_id).exists():
        return [cliente_id]
    return list(permitidos.values_list("id", flat=True))


def _raw_queryset(model):
    return getattr(model, "raw_objects", model._default_manager).all()


def _options_queryset_for_user(user, cliente_id=None):
    cliente_ids = _ava_cliente_ids(user, cliente_id)
    user_model = get_user_model()
    usuarios = user_model.objects.filter(cursos_matriculados__isnull=False).distinct()
    escolas = _raw_queryset(Escola)
    cursos = _raw_queryset(Curso)
    modulos = _raw_queryset(CursoModulo).select_related("curso")
    aulas = _raw_queryset(Aula).select_related("modulo", "modulo__curso")
    eixos = _raw_queryset(Eixo).filter(ativo=True)

    usuarios = usuarios.filter(cliente_id__in=cliente_ids)
    escolas = escolas.filter(cliente_id__in=cliente_ids, is_deleted=False)
    cursos = cursos.filter(cliente_id__in=cliente_ids, is_deleted=False)
    modulos = modulos.filter(curso__cliente_id__in=cliente_ids, is_deleted=False)
    aulas = aulas.filter(modulo__curso__cliente_id__in=cliente_ids, is_deleted=False)
    eixos = eixos.filter(cliente_id__in=cliente_ids, is_deleted=False)

    usuarios = usuarios.order_by("nome", "email")
    escolas = escolas.distinct().order_by("nome")
    cursos = cursos.distinct().order_by("titulo")
    modulos = modulos.distinct().order_by("titulo")
    aulas = aulas.distinct().order_by("titulo")
    eixos = eixos.distinct().order_by("ordem_exibicao", "nome")
    return usuarios, escolas, cursos, modulos, aulas, eixos


def _base_queryset(user, cliente_id=None):
    qs = _raw_queryset(AtividadeTentativa).filter(is_deleted=False).select_related(
        "cliente",
        "aluno",
        "atividade__aula__modulo__curso",
    ).prefetch_related(
        Prefetch(
            "respostas_quiz",
            queryset=_raw_queryset(QuizRespostaItem).filter(is_deleted=False),
        ),
        Prefetch(
            "arquivos",
            queryset=_raw_queryset(AtividadeTentativaArquivo).filter(is_deleted=False),
        ),
    )
    return qs.filter(cliente_id__in=_ava_cliente_ids(user, cliente_id))


def _apply_filters(qs, filtros):
    if filtros["escola_id"]:
        qs = qs.filter(aluno__escola_id=filtros["escola_id"])
    if filtros["usuario_id"]:
        qs = qs.filter(aluno_id=filtros["usuario_id"])
    if filtros["curso_id"]:
        qs = qs.filter(atividade__aula__modulo__curso_id=filtros["curso_id"])
    if filtros["modulo_id"]:
        qs = qs.filter(atividade__aula__modulo_id=filtros["modulo_id"])
    if filtros["aula_id"]:
        qs = qs.filter(atividade__aula_id=filtros["aula_id"])
    if filtros["eixo_id"]:
        qs = qs.filter(
            Q(atividade__eixos=filtros["eixo_id"])
            | Q(atividade__aula__modulo__eixos=filtros["eixo_id"])
            | Q(atividade__aula__modulo__curso__eixos=filtros["eixo_id"])
        ).distinct()
    if filtros["status"]:
        qs = qs.filter(status=filtros["status"])
    if filtros["tipo"]:
        qs = qs.filter(atividade__tipo=filtros["tipo"])
    if filtros["data_inicio"]:
        qs = qs.filter(data_inicio__date__gte=filtros["data_inicio"])
    if filtros["data_fim"]:
        qs = qs.filter(data_inicio__date__lte=filtros["data_fim"])
    if filtros["q"]:
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


def _quiz_resolution_metrics(tentativas_filtradas):
    quiz_tentativas = list(
        tentativas_filtradas.filter(
            atividade__tipo__in=[Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO],
            status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA],
        ).values_list("id", "atividade_id")
    )
    if not quiz_tentativas:
        return {
            "total_previstas": 0,
            "total_respondidas": 0,
            "total_corretas": 0,
            "taxa_resolucao": 0.0,
            "taxa_acerto": 0.0,
        }

    tentativa_ids = [tentativa_id for tentativa_id, _ in quiz_tentativas]
    atividade_ids = {atividade_id for _, atividade_id in quiz_tentativas}
    questoes_por_atividade = dict(
        _raw_queryset(QuizQuestao).filter(is_deleted=False, atividade_id__in=atividade_ids)
        .values("atividade_id")
        .annotate(total=Count("id"))
        .values_list("atividade_id", "total")
    )

    total_previstas = sum(questoes_por_atividade.get(atividade_id, 0) for _, atividade_id in quiz_tentativas)
    total_respondidas = _raw_queryset(QuizRespostaItem).filter(
        is_deleted=False, tentativa_id__in=tentativa_ids
    ).count()
    total_corretas = _raw_queryset(QuizRespostaItem).filter(
        is_deleted=False, tentativa_id__in=tentativa_ids, is_correta=True
    ).count()
    taxa_resolucao = round((total_respondidas / total_previstas) * 100, 1) if total_previstas else 0.0
    taxa_acerto = round((total_corretas / total_respondidas) * 100, 1) if total_respondidas else 0.0
    return {
        "total_previstas": total_previstas,
        "total_respondidas": total_respondidas,
        "total_corretas": total_corretas,
        "taxa_resolucao": taxa_resolucao,
        "taxa_acerto": taxa_acerto,
    }


@ava_management_required
def dashboard(request):
    filtros, data_inicio_raw, data_fim_raw = _extract_dashboard_filters(request)

    tentativas_qs = _apply_filters(_base_queryset(request.user, filtros["cliente_id"]), filtros)

    cliente_ids = _ava_cliente_ids(request.user, filtros["cliente_id"])
    matriculas_qs = _raw_queryset(MatriculaCurso).filter(is_deleted=False, cliente_id__in=cliente_ids).select_related("curso", "aluno")
    cursos_qs = _raw_queryset(Curso).filter(is_deleted=False, cliente_id__in=cliente_ids)
    atividades_qs = _raw_queryset(Atividade).filter(is_deleted=False, cliente_id__in=cliente_ids)
    if filtros["escola_id"]:
        matriculas_qs = matriculas_qs.filter(aluno__escola_id=filtros["escola_id"])

    total_tentativas = tentativas_qs.count()
    total_enviadas = tentativas_qs.filter(status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA]).count()
    total_corrigidas = tentativas_qs.filter(status=AtividadeTentativa.Status.CORRIGIDA).count()
    total_com_anexo = (
        tentativas_qs.filter(
            Q(arquivos__isnull=False)
            | (Q(arquivo_enviado__isnull=False) & ~Q(arquivo_enviado=""))
        )
        .distinct()
        .count()
    )
    taxa_envio = round((total_enviadas / total_tentativas) * 100, 1) if total_tentativas else 0.0
    taxa_correcao = round((total_corrigidas / total_enviadas) * 100, 1) if total_enviadas else 0.0
    media_nota = tentativas_qs.exclude(nota_obtida__isnull=True).aggregate(media=Avg("nota_obtida")).get("media")
    ultima_atividade = tentativas_qs.aggregate(max_data=Max("data_envio")).get("max_data")
    quiz_metrics = _quiz_resolution_metrics(tentativas_qs)

    resumo_por_usuario = (
        tentativas_qs.values("aluno_id", "aluno__nome", "aluno__email")
        .annotate(
            total=Count("id"),
            enviadas=Count("id", filter=Q(status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA])),
            corrigidas=Count("id", filter=Q(status=AtividadeTentativa.Status.CORRIGIDA)),
        )
        .order_by("-total", "aluno__nome")[:10]
    )
    resumo_por_curso = (
        tentativas_qs.values("atividade__aula__modulo__curso_id", "atividade__aula__modulo__curso__titulo")
        .annotate(total=Count("id"))
        .order_by("-total", "atividade__aula__modulo__curso__titulo")[:10]
    )
    resumo_por_modulo = (
        tentativas_qs.values("atividade__aula__modulo_id", "atividade__aula__modulo__titulo")
        .annotate(total=Count("id"))
        .order_by("-total", "atividade__aula__modulo__titulo")[:10]
    )

    paginator = Paginator(tentativas_qs.order_by("-data_inicio"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    usuarios, escolas, cursos, modulos, aulas, eixos = _options_queryset_for_user(
        request.user, filtros["cliente_id"]
    )
    if filtros["escola_id"]:
        usuarios = usuarios.filter(escola_id=filtros["escola_id"])
    if filtros["curso_id"]:
        modulos = modulos.filter(curso_id=filtros["curso_id"])
        aulas = aulas.filter(modulo__curso_id=filtros["curso_id"])
    if filtros["modulo_id"]:
        aulas = aulas.filter(modulo_id=filtros["modulo_id"])

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "filtros": filtros,
        "municipios_ava": request.user.get_ava_clientes_queryset(),
        "pode_gerir_multiplos_avas": request.user.get_ava_clientes_queryset().count() > 1,
        "data_inicio_raw": data_inicio_raw,
        "data_fim_raw": data_fim_raw,
        "status_choices": AtividadeTentativa.Status.choices,
        "tipo_choices": Atividade.Tipo.choices,
        "usuarios": usuarios,
        "escolas": escolas,
        "cursos": cursos,
        "modulos": modulos,
        "aulas": aulas,
        "eixos": eixos,
        "page_obj": page_obj,
        "querystring": query_params.urlencode(),
        "visao_geral": {
            "total_alunos": matriculas_qs.values("aluno_id").distinct().count(),
            "total_matriculas": matriculas_qs.count(),
            "total_cursos": cursos_qs.count(),
            "total_atividades": atividades_qs.count(),
        },
        "metricas": {
            "total_tentativas": total_tentativas,
            "total_enviadas": total_enviadas,
            "total_corrigidas": total_corrigidas,
            "total_com_anexo": total_com_anexo,
            "taxa_envio": taxa_envio,
            "taxa_correcao": taxa_correcao,
            "media_nota": media_nota,
            "ultima_atividade": ultima_atividade,
            "quiz": quiz_metrics,
        },
        "resumo_por_usuario": resumo_por_usuario,
        "resumo_por_curso": resumo_por_curso,
        "resumo_por_modulo": resumo_por_modulo,
    }
    return render(request, "ava/management/dashboard.html", context)


@ava_management_required
def dashboard_relatorio(request, formato):
    if formato not in {"pdf", "xlsx"}:
        raise Http404("Formato de relatório não suportado.")

    filtros, _, _ = _extract_dashboard_filters(request)
    report_data = AVAManagementReportService.build_report(request.user, filtros)

    timestamp = report_data["generated_at"].strftime("%Y%m%d-%H%M%S")
    if formato == "pdf":
        payload = AVAManagementReportService.render_pdf_bytes(report_data)
        response = HttpResponse(payload, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="relatorio-ava-nominal-{timestamp}.pdf"'
        )
        return response

    payload = AVAManagementReportService.render_xlsx_bytes(report_data)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="relatorio-ava-nominal-{timestamp}.xlsx"'
    )
    return response


@ava_management_required
def dashboard_relatorio_entenda(request):
    return render(request, "ava/management/dashboard_report_explained.html")


@ava_management_required
def tentativa_detalhe(request, tentativa_id):
    tentativa_qs = _raw_queryset(AtividadeTentativa).filter(
        is_deleted=False,
        cliente_id__in=_ava_cliente_ids(request.user),
    ).select_related(
        "cliente",
        "aluno",
        "atividade__aula__modulo__curso",
    ).prefetch_related(
        Prefetch(
            "respostas_quiz",
            queryset=_raw_queryset(QuizRespostaItem).filter(is_deleted=False).select_related(
                "questao", "alternativa_selecionada"
            ).order_by("questao__ordem", "questao_id"),
        ),
        Prefetch(
            "arquivos",
            queryset=_raw_queryset(AtividadeTentativaArquivo).filter(is_deleted=False),
        ),
    )
    tentativa = get_object_or_404(tentativa_qs, id=tentativa_id)
    respostas_quiz = list(tentativa.respostas_quiz.all())
    forum_messages = []
    if tentativa.atividade.tipo == Atividade.Tipo.FORUM:
        forum_messages = list(
            _raw_queryset(AtividadeForumMensagem).filter(
                is_deleted=False,
                cliente_id__in=_ava_cliente_ids(request.user),
                atividade=tentativa.atividade,
            )
            .select_related("autor", "resposta_para__autor")
            .prefetch_related(
                Prefetch(
                    "anexos",
                    queryset=_raw_queryset(AtividadeForumAnexo).filter(is_deleted=False),
                )
            )
            .order_by("created_at", "id")
        )

    correcao_form = AtividadeTentativaCorrecaoForm(instance=tentativa)
    if request.method == "POST":
        correcao_form = AtividadeTentativaCorrecaoForm(request.POST, instance=tentativa)
        if correcao_form.is_valid():
            with cliente_scope(tentativa.cliente_id):
                AtividadeService.corrigir_tentativa(
                    tentativa,
                    corretor=request.user,
                    status=correcao_form.cleaned_data["status"],
                    nota_obtida=correcao_form.cleaned_data["nota_obtida"],
                    feedback_tutor=correcao_form.cleaned_data["feedback_tutor"],
                )
            messages.success(request, "Correção salva com sucesso.")
            return redirect("ava:gestao_tentativa_detalhe", tentativa_id=tentativa.id)
        messages.error(request, "Não foi possível salvar a correção. Revise os campos do formulário.")

    return render(
        request,
        "ava/management/tentativa_detalhe.html",
        {
            "tentativa": tentativa,
            "respostas_quiz": respostas_quiz,
            "correcao_form": correcao_form,
            "forum_messages": forum_messages,
        },
    )
