from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ava.models import Curso, TrilhaFormativa
from ava.services import InscricaoService

def catalogo_cursos(request):
    """
    Página pública exibindo os cursos disponíveis
    """
    cursos = Curso.objects.filter(status="publicado").order_by("-created_at")
    trilhas = TrilhaFormativa.objects.filter(is_active=True)
    
    return render(request, "ava/public/catalogo.html", {
        "cursos": cursos,
        "trilhas": trilhas
    })

def detalhes_curso_publico(request, slug):
    """
    Landing page do curso.
    """
    curso = get_object_or_404(Curso, slug=slug, status="publicado")
    
    # Se o usuário está logado e matriculado, manda pro curso.
    if request.user.is_authenticated:
        if curso.matriculas.filter(aluno=request.user, status="ativa").exists():
            return redirect("ava:aluno_curso_detalhe", slug=slug)

    return render(request, "ava/public/detalhes.html", {"curso": curso})

@login_required
def matricular_curso_agora(request, slug):
    """
    Endpoint (POST) para auto-inscrição em cursos abertos.
    """
    if request.method == "POST":
        curso = get_object_or_404(Curso, slug=slug, is_aberto=True, status="publicado")
        InscricaoService.matricular_aluno_curso(request.user, curso)
        messages.success(request, f"Matrícula realizada com sucesso no curso {curso.titulo}!")
        return redirect("ava:aluno_curso_detalhe", slug=slug)
    
    return redirect("ava:catalogo")
