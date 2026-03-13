from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ava.models import Curso, MatriculaCurso, Aula, Atividade, AtividadeTentativa
from ava.services import ProgressoService, AtividadeService

@login_required
def dashboard(request):
    """
    Dashboard do Aluno mostrando matrículas ativas e resumo.
    """
    matriculas = MatriculaCurso.objects.filter(aluno=request.user, status="ativa").select_related("curso")
    return render(request, "ava/student/dashboard.html", {"matriculas": matriculas})

@login_required
def curso_detalhe(request, slug):
    """
    Página do curso matriculado. Exibe os módulos e o progresso.
    """
    matricula = get_object_or_404(
        MatriculaCurso.objects.select_related("curso"), 
        aluno=request.user, 
        curso__slug=slug
    )
    modulos = matricula.curso.modulos.filter(is_active=True).prefetch_related("aulas")
    
    return render(request, "ava/student/curso.html", {
        "matricula": matricula,
        "curso": matricula.curso,
        "modulos": modulos
    })

@login_required
def acessar_aula(request, curso_slug, aula_id):
    """
    Página de consumo da aula (vídeo, textos).
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    conteudos = aula.conteudos.all().order_by("ordem")
    atividades = aula.atividades.all().order_by("titulo")

    # Marca a aula como iniciada / cria o progresso
    ProgressoService._garantir_progressos(matricula, aula)

    return render(request, "ava/student/aula.html", {
        "matricula": matricula,
        "aula": aula,
        "conteudos": conteudos,
        "atividades": atividades
    })

@login_required
def marcar_conteudo(request, conteudo_id):
    """
    Endpoint HTMX/Fetch para marcar conteúdo como visualizado.
    """
    if request.method == "POST":
        ProgressoService.marcar_conteudo_visualizado(request.user, conteudo_id)
        # Retorna um fragmento HTMX ou um JSON. 
        # Exemplo simples HTMX: redireciona ou apenas diz 'OK' e atualiza a div.
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def responder_atividade(request, curso_slug, aula_id, atividade_id):
    """
    Página de resposta da atividade/questionário.
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    atividade = get_object_or_404(Atividade, id=atividade_id, aula=aula)
    
    # Verifica tentativas ou inicia uma nova
    tentativa, erro = AtividadeService.iniciar_tentativa(request.user, atividade)
    
    if erro:
        messages.warning(request, erro)
        return redirect('ava:aluno_acessar_aula', curso_slug=curso_slug, aula_id=aula_id)

    if request.method == "POST":
        if atividade.tipo in [Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO]:
            dados_respostas = {k: v for k, v in request.POST.items() if k.isdigit()}
            AtividadeService.submeter_quiz(tentativa, dados_respostas)
            messages.success(request, "Questionário enviado com sucesso!")
        else:
            texto = request.POST.get("texto_resposta", "")
            arquivo = request.FILES.get("arquivo_enviado")
            AtividadeService.submeter_tarefa_discursiva(tentativa, texto, arquivo)
            messages.success(request, "Atividade enviada com sucesso!")
            
        return redirect('ava:aluno_acessar_aula', curso_slug=curso_slug, aula_id=aula_id)

    # Se for GET, renderiza a prova
    questoes = []
    if atividade.tipo in [Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO]:
        questoes = atividade.questoes.all().prefetch_related("alternativas")

    return render(request, "ava/student/atividade.html", {
        "curso": matricula.curso,
        "aula": aula,
        "atividade": atividade,
        "questoes": questoes,
        "tentativa": tentativa
    })
