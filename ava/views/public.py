from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ava.models import Curso, MatriculaCurso, TrilhaFormativa
from ava.services import InscricaoService


def catalogo_cursos(request):
    """
    Pagina publica exibindo os cursos disponiveis.
    """
    cursos = list(Curso.objects.filter(status="publicado").order_by("-created_at"))
    trilhas = TrilhaFormativa.objects.filter(is_active=True)

    matriculados_ids = set()
    if request.user.is_authenticated and cursos:
        matriculados_ids = set(
            MatriculaCurso.objects.filter(
                aluno=request.user,
                curso_id__in=[curso.id for curso in cursos],
                status=MatriculaCurso.Status.ATIVA,
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
        if curso.matriculas.filter(aluno=request.user, status=MatriculaCurso.Status.ATIVA).exists():
            return redirect("ava:aluno_curso_detalhe", slug=slug)

    return render(request, "ava/public/detalhes.html", {"curso": curso})


@login_required
def matricular_curso_agora(request, slug):
    """
    Endpoint (POST) para auto-inscricao em cursos abertos.
    """
    if request.method == "POST":
        curso = get_object_or_404(Curso, slug=slug, is_aberto=True, status="publicado")
        InscricaoService.matricular_aluno_curso(request.user, curso)
        messages.success(request, f"Matricula realizada com sucesso no curso {curso.titulo}!")
        return redirect("ava:aluno_curso_detalhe", slug=slug)

    return redirect("ava:catalogo")
