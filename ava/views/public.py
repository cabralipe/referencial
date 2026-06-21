from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ava.models import Curso, MatriculaCurso, TrilhaFormativa
from ava.services import InscricaoService
from ava.services.access_control import (
    course_eixo_block_message,
    filter_courses_for_user_by_eixo,
    user_can_access_course_by_eixo,
)
from core.models import Eixo
from core.models import Usuario


VISIBLE_ENROLLMENT_STATUSES = [
    MatriculaCurso.Status.ATIVA,
    MatriculaCurso.Status.CONCLUIDA,
]

CURSO_PPP_SLUG = "implementacao-referencial-curricular-ppp-2"

def _next_or_catalogo(request):
    return request.POST.get("next") or request.META.get("HTTP_REFERER") or redirect("ava:catalogo").url


def catalogo_cursos(request):
    """
    Página pública exibindo os cursos disponíveis.
    """
    cursos_qs = Curso.objects.filter(status=Curso.Status.PUBLICADO).prefetch_related("eixos")
    if (
        request.user.is_authenticated
        and getattr(request.user, "role", None) == Usuario.Role.PROFESSOR
        and getattr(request.user, "seguimento", "") == Usuario.Seguimento.PROFISSIONAL_APOIO
    ):
        cursos_qs = cursos_qs.exclude(slug=CURSO_PPP_SLUG)

    eixos = Eixo.objects.filter(ativo=True).order_by("ordem_exibicao", "nome")
    eixo_id = (request.GET.get("eixo") or "").strip()
    eixo_selecionado = None
    if eixo_id.isdigit():
        eixo_selecionado = eixos.filter(pk=int(eixo_id)).first()
        if eixo_selecionado:
            cursos_qs = cursos_qs.filter(eixos=eixo_selecionado)

    cursos_qs = filter_courses_for_user_by_eixo(cursos_qs, request.user)
    cursos = [
        curso
        for curso in cursos_qs.order_by("-created_at")
        if user_can_access_course_by_eixo(request.user, curso)
    ]
    trilhas = TrilhaFormativa.objects.filter(is_active=True)
    matriculados_ids = set()
    if request.user.is_authenticated and cursos:
        matriculados_ids = set(
            MatriculaCurso.objects.filter(
                aluno=request.user,
                curso_id__in=[curso.id for curso in cursos],
                status__in=VISIBLE_ENROLLMENT_STATUSES,
            ).values_list("curso_id", flat=True)
        )

    for curso in cursos:
        curso.aluno_matriculado = curso.id in matriculados_ids

    popup_eixos_ativo = bool(
        getattr(getattr(request.user, "cliente", None), "popup_eixos_ativo", False)
    )
    eixos_pendente = popup_eixos_ativo and bool(getattr(request.user, "eixos_pendente", False))
    eixos_para_selecao = (
        list(_eixos_disponiveis_para(request.user)) if eixos_pendente else []
    )

    return render(
        request,
        "ava/public/catalogo.html",
        {
            "cursos": cursos,
            "trilhas": trilhas,
            "eixos": eixos,
            "eixo_selecionado": eixo_selecionado,
            "eixos_pendente": eixos_pendente and bool(eixos_para_selecao),
            "eixos_para_selecao": eixos_para_selecao,
        },
    )


def detalhes_curso_publico(request, slug):
    """
    Landing page do curso.
    """
    curso = get_object_or_404(Curso, slug=slug, status="publicado")
    acesso_bloqueado = not user_can_access_course_by_eixo(request.user, curso)
    motivo_bloqueio = course_eixo_block_message(curso) if acesso_bloqueado else ""

    # Se o usuário está logado e matriculado, manda para o curso.
    if request.user.is_authenticated and not acesso_bloqueado:
        if curso.matriculas.filter(aluno=request.user, status__in=VISIBLE_ENROLLMENT_STATUSES).exists():
            return redirect("ava:aluno_curso_detalhe", slug=slug)

    return render(
        request,
        "ava/public/detalhes.html",
        {"curso": curso, "acesso_bloqueado": acesso_bloqueado, "motivo_bloqueio": motivo_bloqueio},
    )


@login_required
@require_POST
def registrar_seguimento_professor(request):
    if getattr(request.user, "role", None) != Usuario.Role.PROFESSOR:
        messages.error(request, "Apenas usuários com perfil de professor podem registrar seguimento.")
        return HttpResponseRedirect(_next_or_catalogo(request))

    if getattr(request.user, "seguimento", ""):
        return HttpResponseRedirect(_next_or_catalogo(request))

    seguimento = (request.POST.get("seguimento") or "").strip()
    if seguimento not in Usuario.Seguimento.values:
        messages.error(request, "Selecione um seguimento válido para continuar.")
        return HttpResponseRedirect(_next_or_catalogo(request))

    request.user.seguimento = seguimento
    request.user.save(update_fields=["seguimento"])
    messages.success(request, "Seguimento registrado com sucesso.")
    return HttpResponseRedirect(_next_or_catalogo(request))


def _eixos_disponiveis_para(user):
    """Eixos ativos do cliente do usuário, usados na seleção dentro do AVA."""
    cliente_id = getattr(user, "cliente_id", None)
    if not cliente_id:
        return Eixo.objects.none()
    return Eixo.objects.filter(
        cliente_id=cliente_id, ativo=True
    ).order_by("ordem_exibicao", "nome")


@login_required
@require_POST
def selecionar_eixos(request):
    """Salva os eixos escolhidos pelo usuário ao entrar no AVA.

    A seleção deixou de ser um popup obrigatório do Referencial/PPP e passou a
    ocorrer somente aqui, no módulo AVA, quando o usuário ainda não tem eixos.
    """
    if not getattr(request.user, "eixos_pendente", False):
        return HttpResponseRedirect(_next_or_catalogo(request))

    ids_brutos = request.POST.getlist("eixos")
    ids = [int(valor) for valor in ids_brutos if str(valor).isdigit()]
    eixos = list(_eixos_disponiveis_para(request.user).filter(pk__in=ids))
    if not eixos:
        messages.error(request, "Selecione ao menos um eixo para continuar.")
        return HttpResponseRedirect(_next_or_catalogo(request))

    request.user.eixos.add(*eixos)
    messages.success(request, "Eixos registrados com sucesso. Bons estudos!")
    return HttpResponseRedirect(_next_or_catalogo(request))


@login_required
def matricular_curso_agora(request, slug):
    """
    Endpoint (POST) para autoinscrição em cursos abertos.
    """
    if request.method == "POST":
        curso = get_object_or_404(Curso, slug=slug, is_aberto=True, status="publicado")
        if not user_can_access_course_by_eixo(request.user, curso):
            messages.warning(request, course_eixo_block_message(curso))
            return redirect("ava:detalhes_curso", slug=slug)
        status_anterior = (
            MatriculaCurso.objects.filter(curso=curso, aluno=request.user).values_list("status", flat=True).first()
        )
        matricula, created = InscricaoService.matricular_aluno_curso(request.user, curso, autor_matricula=request.user)
        if created:
            messages.success(request, f"Matrícula realizada com sucesso no curso {curso.titulo}!")
        elif status_anterior in {MatriculaCurso.Status.CONCLUIDA, MatriculaCurso.Status.SUSPENSA, MatriculaCurso.Status.CANCELADA}:
            messages.success(request, f"Matrícula reativada com sucesso no curso {curso.titulo}!")
        else:
            messages.info(request, f"Você já possui acesso ao curso {curso.titulo}.")
        return redirect("ava:aluno_curso_detalhe", slug=slug)

    return redirect("ava:catalogo")

