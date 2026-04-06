from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ava.models import Curso, MatriculaCurso, TrilhaFormativa
from ava.services import InscricaoService
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
    Pagina publica exibindo os cursos disponiveis.
    """
    cursos_qs = Curso.objects.filter(status=Curso.Status.PUBLICADO)
    if (
        request.user.is_authenticated
        and getattr(request.user, "role", None) == Usuario.Role.PROFESSOR
        and getattr(request.user, "seguimento", "") == Usuario.Seguimento.PROFISSIONAL_APOIO
    ):
        cursos_qs = cursos_qs.exclude(slug=CURSO_PPP_SLUG)

    cursos = list(cursos_qs.order_by("-created_at"))
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

    return render(
        request,
        "ava/public/catalogo.html",
        {
            "cursos": cursos,
            "trilhas": trilhas,
        },
    )


def detalhes_curso_publico(request, slug):
    """
    Landing page do curso.
    """
    curso = get_object_or_404(Curso, slug=slug, status="publicado")

    # Se o usuario esta logado e matriculado, manda para o curso.
    if request.user.is_authenticated:
        if curso.matriculas.filter(aluno=request.user, status__in=VISIBLE_ENROLLMENT_STATUSES).exists():
            return redirect("ava:aluno_curso_detalhe", slug=slug)

    return render(request, "ava/public/detalhes.html", {"curso": curso})


@login_required
@require_POST
def registrar_seguimento_professor(request):
    if getattr(request.user, "role", None) != Usuario.Role.PROFESSOR:
        messages.error(request, "Apenas usuarios com perfil de professor podem registrar seguimento.")
        return HttpResponseRedirect(_next_or_catalogo(request))

    if getattr(request.user, "seguimento", ""):
        return HttpResponseRedirect(_next_or_catalogo(request))

    seguimento = (request.POST.get("seguimento") or "").strip()
    if seguimento not in Usuario.Seguimento.values:
        messages.error(request, "Selecione um seguimento valido para continuar.")
        return HttpResponseRedirect(_next_or_catalogo(request))

    request.user.seguimento = seguimento
    request.user.save(update_fields=["seguimento"])
    messages.success(request, "Seguimento registrado com sucesso.")
    return HttpResponseRedirect(_next_or_catalogo(request))


@login_required
def matricular_curso_agora(request, slug):
    """
    Endpoint (POST) para auto-inscricao em cursos abertos.
    """
    if request.method == "POST":
        curso = get_object_or_404(Curso, slug=slug, is_aberto=True, status="publicado")
        status_anterior = (
            MatriculaCurso.objects.filter(curso=curso, aluno=request.user).values_list("status", flat=True).first()
        )
        matricula, created = InscricaoService.matricular_aluno_curso(request.user, curso, autor_matricula=request.user)
        if created:
            messages.success(request, f"Matricula realizada com sucesso no curso {curso.titulo}!")
        elif status_anterior in {MatriculaCurso.Status.CONCLUIDA, MatriculaCurso.Status.SUSPENSA, MatriculaCurso.Status.CANCELADA}:
            messages.success(request, f"Matricula reativada com sucesso no curso {curso.titulo}!")
        else:
            messages.info(request, f"Voce ja possui acesso ao curso {curso.titulo}.")
        return redirect("ava:aluno_curso_detalhe", slug=slug)

    return redirect("ava:catalogo")
