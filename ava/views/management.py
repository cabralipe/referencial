from __future__ import annotations

from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.db.models import Avg, Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render

from ava.forms import AtividadeTentativaCorrecaoForm
from ava.models import (
    Atividade,
    AtividadeForumMensagem,
    AtividadeTentativa,
    Aula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    QuizQuestao,
    QuizRespostaItem,
)
from ava.services import AVAManagementReportService, AtividadeService
from core.models import Usuario


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
        "usuario_id": _parse_int(request.GET.get("usuario")),
        "curso_id": _parse_int(request.GET.get("curso")),
        "modulo_id": _parse_int(request.GET.get("modulo")),
        "aula_id": _parse_int(request.GET.get("aula")),
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
            raise PermissionDenied("Voce nao possui permissao para acessar a gestao do AVA.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _is_super_admin(user) -> bool:
    return getattr(user, "role", None) == Usuario.Role.SUPER_ADMIN


def _options_queryset_for_user(user):
    user_model = get_user_model()
    usuarios = user_model.objects.filter(cursos_matriculados__isnull=False).distinct()
    cursos = Curso.objects.all()
    modulos = CursoModulo.objects.select_related("curso").all()
    aulas = Aula.objects.select_related("modulo", "modulo__curso").all()

    if not _is_super_admin(user):
        usuarios = usuarios.filter(cliente_id=user.cliente_id)
        cursos = cursos.filter(cliente_id=user.cliente_id)
        modulos = modulos.filter(curso__cliente_id=user.cliente_id)
        aulas = aulas.filter(modulo__curso__cliente_id=user.cliente_id)

    usuarios = usuarios.order_by("nome", "email")
    cursos = cursos.distinct().order_by("titulo")
    modulos = modulos.distinct().order_by("titulo")
    aulas = aulas.distinct().order_by("titulo")
    return usuarios, cursos, modulos, aulas


def _base_queryset(user):
    qs = AtividadeTentativa.objects.select_related(
        "aluno",
        "atividade__aula__modulo__curso",
    ).prefetch_related("respostas_quiz")
    if not _is_super_admin(user):
        qs = qs.filter(cliente_id=user.cliente_id)
    return qs


def _apply_filters(qs, filtros):
    if filtros["usuario_id"]:
        qs = qs.filter(aluno_id=filtros["usuario_id"])
    if filtros["curso_id"]:
        qs = qs.filter(atividade__aula__modulo__curso_id=filtros["curso_id"])
    if filtros["modulo_id"]:
        qs = qs.filter(atividade__aula__modulo_id=filtros["modulo_id"])
    if filtros["aula_id"]:
        qs = qs.filter(atividade__aula_id=filtros["aula_id"])
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
        QuizQuestao.objects.filter(atividade_id__in=atividade_ids)
        .values("atividade_id")
        .annotate(total=Count("id"))
        .values_list("atividade_id", "total")
    )

    total_previstas = sum(questoes_por_atividade.get(atividade_id, 0) for _, atividade_id in quiz_tentativas)
    total_respondidas = QuizRespostaItem.objects.filter(tentativa_id__in=tentativa_ids).count()
    total_corretas = QuizRespostaItem.objects.filter(tentativa_id__in=tentativa_ids, is_correta=True).count()
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

    tentativas_qs = _apply_filters(_base_queryset(request.user), filtros)

    matriculas_qs = MatriculaCurso.objects.select_related("curso", "aluno")
    cursos_qs = Curso.objects.all()
    atividades_qs = Atividade.objects.all()
    if not _is_super_admin(request.user):
        matriculas_qs = matriculas_qs.filter(cliente_id=request.user.cliente_id)
        cursos_qs = cursos_qs.filter(cliente_id=request.user.cliente_id)
        atividades_qs = atividades_qs.filter(cliente_id=request.user.cliente_id)

    total_tentativas = tentativas_qs.count()
    total_enviadas = tentativas_qs.filter(status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA]).count()
    total_corrigidas = tentativas_qs.filter(status=AtividadeTentativa.Status.CORRIGIDA).count()
    total_com_anexo = tentativas_qs.exclude(arquivo_enviado="").exclude(arquivo_enviado__isnull=True).count()
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

    usuarios, cursos, modulos, aulas = _options_queryset_for_user(request.user)
    if filtros["curso_id"]:
        modulos = modulos.filter(curso_id=filtros["curso_id"])
        aulas = aulas.filter(modulo__curso_id=filtros["curso_id"])
    if filtros["modulo_id"]:
        aulas = aulas.filter(modulo_id=filtros["modulo_id"])

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "filtros": filtros,
        "data_inicio_raw": data_inicio_raw,
        "data_fim_raw": data_fim_raw,
        "status_choices": AtividadeTentativa.Status.choices,
        "tipo_choices": Atividade.Tipo.choices,
        "usuarios": usuarios,
        "cursos": cursos,
        "modulos": modulos,
        "aulas": aulas,
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
        raise Http404("Formato de relatorio nao suportado.")

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
def tentativa_detalhe(request, tentativa_id):
    tentativa_qs = AtividadeTentativa.objects.select_related(
        "aluno",
        "atividade__aula__modulo__curso",
    ).prefetch_related("respostas_quiz__questao", "respostas_quiz__alternativa_selecionada")
    if not _is_super_admin(request.user):
        tentativa_qs = tentativa_qs.filter(cliente_id=request.user.cliente_id)
    tentativa = get_object_or_404(tentativa_qs, id=tentativa_id)
    respostas_quiz = tentativa.respostas_quiz.all().order_by("questao__ordem", "questao_id")
    forum_messages = []
    if tentativa.atividade.tipo == Atividade.Tipo.FORUM:
        forum_messages = list(
            AtividadeForumMensagem.objects.filter(atividade=tentativa.atividade)
            .select_related("autor", "resposta_para__autor")
            .prefetch_related("anexos")
            .order_by("created_at", "id")
        )

    correcao_form = AtividadeTentativaCorrecaoForm(instance=tentativa)
    if request.method == "POST":
        correcao_form = AtividadeTentativaCorrecaoForm(request.POST, instance=tentativa)
        if correcao_form.is_valid():
            AtividadeService.corrigir_tentativa(
                tentativa,
                corretor=request.user,
                status=correcao_form.cleaned_data["status"],
                nota_obtida=correcao_form.cleaned_data["nota_obtida"],
                feedback_tutor=correcao_form.cleaned_data["feedback_tutor"],
            )
            messages.success(request, "Correcao salva com sucesso.")
            return redirect("ava:gestao_tentativa_detalhe", tentativa_id=tentativa.id)
        messages.error(request, "Nao foi possivel salvar a correcao. Revise os campos do formulario.")

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
